#!/usr/bin/env python3
"""Route one task to its deterministic local, setup, or executor transition."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from automation_readiness import task_readiness


ROUTINE_EXTERNAL_TASK_TYPES = {
    "comment",
    "direct-inbound",
    "direct-message",
    "engagement-burst",
    "engagement-burst-execution",
    "publication-execution",
    "publication-opportunity",
    "reaction",
    "reply",
    "soft-reciprocity",
}

APPROVAL_SEEKING_PATTERNS = (
    re.compile(r"\bpost this\s*\?", re.IGNORECASE),
    re.compile(r"\b(?:should|shall|may|can) i\s+(?:post|publish|send|reply|comment|react|connect)\b", re.IGNORECASE),
    re.compile(r"\b(?:do|would) you (?:want|like) me to\s+(?:post|publish|send|reply|comment|react|connect|continue)\b", re.IGNORECASE),
    re.compile(r"\bwant me to\s+(?:post|publish|send|reply|comment|react|connect|continue)\b", re.IGNORECASE),
    re.compile(r"\b(?:approve|confirm) (?:this|the)\s+(?:post|publication|comment|reply|message|action)\b", re.IGNORECASE),
)


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def _receipt(consent: dict[str, Any]) -> str | None:
    authorization = consent.get("authorization_receipt", {})
    if not isinstance(authorization, dict):
        return None
    receipt_id = authorization.get("receipt_id")
    return str(receipt_id) if receipt_id else None


def _is_external(task: dict[str, Any]) -> bool:
    task_type = str(task.get("task_type", ""))
    action_lane = str(task.get("action_lane", ""))
    return (
        task_type in ROUTINE_EXTERNAL_TASK_TYPES
        or action_lane in {"direct-inbound", "proactive", "soft-reciprocity"}
        or task.get("external_action") is True
    )


def _identity_mismatch(state: dict[str, Any]) -> bool:
    if state.get("verified_account_identity_mismatch") is True:
        return True
    dispatcher = state.get("dispatcher", {})
    if not isinstance(dispatcher, dict):
        return False
    binding = dispatcher.get("browser_binding", {})
    return isinstance(binding, dict) and (
        binding.get("status") == "identity-mismatch"
        or binding.get("verified_identity_mismatch") is True
    )


def _ambiguous_outcome(task: dict[str, Any]) -> bool:
    return (
        task.get("external_outcome_ambiguous") is True
        or task.get("external_outcome") in {"ambiguous", "unknown", "verification-required"}
        or task.get("status") == "ambiguous-reconciliation"
    )


def authorization_contract(
    task: dict[str, Any],
    consent: dict[str, Any],
    state: dict[str, Any],
    executor: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the deterministic execution boundary for one dispatched task."""
    external = _is_external(task)
    receipt_id = _receipt(consent)
    active = consent.get("status") == "active" and receipt_id is not None
    base = {
        "schema_version": "1.0",
        "routine_external_action": external,
        "receipt_id": receipt_id,
        "setup_input_required": False,
        "routine_transition_is_deterministic": True,
        "owner_input_required": False,
        "status_response_terminal": False,
        "after_owner_status_response": "run-audit-dispatch-and-resume-current-lease",
        "required_terminal_states": [
            "verified-completed",
            "hard-blocked",
            "ambiguous-reconciliation",
        ],
    }
    if not external:
        return {
            **base,
            "mode": "automatic-internal",
            "decision": "execute",
            "executor_route_configured": False,
            "reason": "internal campaign work proceeds through the local dispatcher",
        }
    if not active:
        return {
            **base,
            "mode": "configuration-required",
            "decision": "pause",
            "setup_input_required": True,
            "routine_transition_is_deterministic": False,
            "owner_input_required": True,
            "executor_route_configured": False,
            "reason": "campaign operating receipt is missing, revoked, or invalid",
        }
    if _identity_mismatch(state):
        return {
            **base,
            "mode": "identity-repair-required",
            "decision": "pause",
            "executor_route_configured": False,
            "reason": "verified LinkedIn account identity differs from the campaign receipt",
        }
    if _ambiguous_outcome(task):
        return {
            **base,
            "mode": "reconcile-before-retry",
            "decision": "pause",
            "executor_route_configured": False,
            "reason": "external outcome is ambiguous and must be verified before retry",
        }
    readiness = task_readiness(task, executor or {})
    if readiness.get("zero_human_ready") is not True:
        return {
            **base,
            "mode": "executor-readiness-required",
            "decision": "pause",
            "executor_route_configured": True,
            "setup_input_required": False,
            "routine_transition_is_deterministic": True,
            "owner_input_required": False,
            "reason": "the unattended executor has not yet proved coverage for this action class",
            "automation_readiness": readiness,
        }
    return {
        **base,
        "mode": "unattended-executor",
        "decision": "execute",
        "executor_route_configured": True,
        "reason": "the campaign receipt and verified executor cover this action class",
        "automation_readiness": readiness,
        "execution_sequence": [
            "repair-tier-3-voice-violations",
            "verify-current-duplicate-and-cooldown-evidence",
            "enqueue-canonical-leased-action",
            "daemon-executes-and-verifies-exactly-once",
            "daemon-persists-durable-evidence",
            "run-audit-and-dispatch-next-work",
        ],
    }


def guard_output(contract: dict[str, Any], text: str) -> dict[str, Any]:
    """Keep routine output aligned with the deterministic dispatcher transition."""
    matches = [pattern.pattern for pattern in APPROVAL_SEEKING_PATTERNS if pattern.search(text)]
    deterministic = contract.get("routine_transition_is_deterministic") is True
    valid = not (deterministic and matches)
    return {
        "valid": valid,
        "workflow_choice_prompt_detected": bool(matches),
        "matched_pattern_count": len(matches),
        "required_action": (
            "enqueue-and-return-to-dispatcher"
            if not valid and contract.get("decision") == "execute"
            else "record-executor-readiness-and-continue-eligible-local-work"
            if not valid and contract.get("mode") == "executor-readiness-required"
            else "resume-outcome-reconciliation"
            if not valid
            else "none"
        ),
    }


def find_task(queue: dict[str, Any], task_id: str) -> dict[str, Any]:
    items = queue.get("items", [])
    if not isinstance(items, list):
        raise ValueError("work-queue.json items must be an array")
    for item in items:
        if isinstance(item, dict) and item.get("task_id") == task_id:
            return item
    raise ValueError(f"unknown task_id: {task_id}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state_dir", type=Path)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--task-id")
    source.add_argument("--task-json")
    parser.add_argument("--output-text")
    args = parser.parse_args()
    state_dir = args.state_dir.expanduser().resolve()
    try:
        state = load_object(state_dir / "campaign-state.json")
        consent = load_object(state_dir / "consent-record.json")
        executor = load_object(state_dir / "external-executor.json")
        if args.task_json:
            task = json.loads(args.task_json)
            if not isinstance(task, dict):
                raise ValueError("--task-json must decode to an object")
        else:
            task = find_task(load_object(state_dir / "work-queue.json"), str(args.task_id))
        contract = authorization_contract(task, consent, state, executor)
        result: dict[str, Any] = {"valid": True, "authorization": contract}
        if args.output_text is not None:
            result["output_guard"] = guard_output(contract, args.output_text)
            result["valid"] = result["output_guard"]["valid"]
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result["valid"] else 2
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
