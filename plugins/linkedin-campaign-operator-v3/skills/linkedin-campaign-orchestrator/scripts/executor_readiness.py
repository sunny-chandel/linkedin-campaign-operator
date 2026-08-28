#!/usr/bin/env python3
"""Evaluate unattended official-API readiness for external campaign tasks."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping

from credential_manager import credential_availability


WRITE_SCOPES = {"w_member_social", "w_member_social_feed"}
READ_SCOPES = {"r_member_social", "r_member_social_feed"}
MUTATING_ACTION_CLASSES = {"publication", "comment", "reply", "reaction"}
UNSUPPORTED_PUBLIC_ACTION_CLASSES = {
    "connection-invitation",
    "direct-message",
    "follow",
}

TASK_CLASS_MAP = {
    "comment": "comment",
    "direct-message": "direct-message",
    "publication-execution": "publication",
    "publication-opportunity": "publication",
    "reaction": "reaction",
    "reply": "reply",
}

ACTION_CLASS_ALIASES = {
    "connect": "connection-invitation",
    "connection": "connection-invitation",
    "connection-invitation": "connection-invitation",
    "dm": "direct-message",
    "direct-message": "direct-message",
    "follow": "follow",
    "like": "reaction",
    "message": "direct-message",
    "post": "publication",
    "publish": "publication",
    "publication": "publication",
    "react": "reaction",
    "reaction": "reaction",
    "comment": "comment",
    "reply": "reply",
}


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def normalize_action_class(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower().replace("_", "-")
    return ACTION_CLASS_ALIASES.get(normalized, normalized or None)


def task_action_classes(task: Mapping[str, Any]) -> set[str]:
    """Return only external mutation classes; read-only LinkedIn work returns empty."""
    classes: set[str] = set()
    actions = task.get("actions")
    if isinstance(actions, list):
        for action in actions:
            if not isinstance(action, Mapping):
                continue
            action_class = normalize_action_class(
                action.get("action_class") or action.get("action_type")
            )
            if action_class:
                classes.add(action_class)
    direct_class = normalize_action_class(task.get("action_class") or task.get("action_type"))
    if direct_class:
        classes.add(direct_class)
    task_type = str(task.get("task_type") or "").strip().lower()
    if not classes and task_type in TASK_CLASS_MAP:
        classes.add(TASK_CLASS_MAP[task_type])
    if not classes and task_type in {"engagement-burst", "engagement-burst-execution"}:
        classes.add("comment")
    if not classes and str(task.get("action_lane") or "") == "direct-inbound":
        classes.add("reply")
    return classes


def readiness_report(
    executor: Mapping[str, Any],
    required_action_classes: set[str],
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    environment = os.environ if environ is None else environ
    supported = {
        action_class
        for value in executor.get("supported_action_classes", [])
        if (action_class := normalize_action_class(value))
    }
    declared_scopes = {
        str(value) for value in executor.get("declared_scopes", []) if isinstance(value, str)
    }
    missing: list[str] = []
    mode = str(executor.get("mode") or "unconfigured")
    fixture_mode = mode == "test-fixture" and executor.get("test_fixture") is True
    if executor.get("status") != "active":
        missing.append("executor-status-active")
    if executor.get("unattended") is not True:
        missing.append("unattended-executor-enabled")
    if executor.get("interactive_fallback_enabled") is not False:
        missing.append("interactive-execution-route-disabled")
    if mode not in {"official-linkedin-api", "test-fixture"}:
        missing.append("supported-executor-mode")
    if mode == "test-fixture" and not fixture_mode:
        missing.append("explicit-test-fixture")
    verification = executor.get("verification", {})
    if not isinstance(verification, Mapping):
        verification = {}
    if verification.get("status") != "passed":
        missing.append("executor-verification-passed")
    if verification.get("identity_verified") is not True:
        missing.append("verified-actor-identity")
    if required_action_classes & MUTATING_ACTION_CLASSES:
        if not fixture_mode and not (declared_scopes & WRITE_SCOPES):
            missing.append("linkedin-write-scope")
        if not fixture_mode and not (declared_scopes & READ_SCOPES):
            missing.append("linkedin-read-scope-for-result-verification")
        if verification.get("write_scope_verified") is not True:
            missing.append("verified-write-scope")
        if verification.get("read_scope_verified") is not True:
            missing.append("verified-read-scope")
    if not fixture_mode:
        credentials = credential_availability(executor, environment)
        if not credentials["access_token_resolvable"]:
            missing.append("access-token-or-programmatic-refresh")
        if not credentials["available"]["actor_urn"]:
            missing.append("verified-actor-urn")
        if not credentials["programmatic_refresh_ready"]:
            missing.append("programmatic-token-refresh")
    unsupported = sorted(required_action_classes & UNSUPPORTED_PUBLIC_ACTION_CLASSES)
    uncovered = sorted(required_action_classes - supported)
    if unsupported:
        missing.extend(f"unsupported-action-class:{value}" for value in unsupported)
    if uncovered:
        missing.extend(f"uncovered-action-class:{value}" for value in uncovered)
    missing = list(dict.fromkeys(missing))
    ready = not missing
    return {
        "schema_version": "1.0",
        "unattended_ready": ready,
        "transition": "enqueue-for-executor" if ready else "continue-local-lanes",
        "executor_state": "ready" if ready else "setup-pending",
        "setup_input_required": False,
        "interactive_fallback_enabled": False,
        "executor_mode": mode,
        "required_action_classes": sorted(required_action_classes),
        "supported_action_classes": sorted(supported),
        "missing_capabilities": missing,
    }


def task_readiness(
    task: Mapping[str, Any],
    executor: Mapping[str, Any],
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    classes = task_action_classes(task)
    if not classes:
        return {
            "schema_version": "1.0",
            "unattended_ready": True,
            "transition": "execute-read-only-or-internal",
            "executor_state": "not-required",
            "setup_input_required": False,
            "interactive_fallback_enabled": False,
            "executor_mode": "not-required",
            "required_action_classes": [],
            "supported_action_classes": [],
            "missing_capabilities": [],
        }
    return readiness_report(executor, classes, environ)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state_dir", type=Path)
    parser.add_argument("--task-json")
    parser.add_argument("--require-all", action="store_true")
    args = parser.parse_args()
    state_dir = args.state_dir.expanduser().resolve()
    try:
        executor = load_object(state_dir / "external-executor.json")
        if args.task_json:
            task = json.loads(args.task_json)
            if not isinstance(task, dict):
                raise ValueError("--task-json must decode to an object")
            report = task_readiness(task, executor)
        else:
            config = load_object(state_dir / "campaign-config.json")
            required = config.get("autonomous_execution", {}).get(
                "required_action_classes", sorted(MUTATING_ACTION_CLASSES)
            )
            required_classes = {
                action_class
                for value in required
                if (action_class := normalize_action_class(value))
            }
            report = readiness_report(executor, required_classes)
        print(json.dumps({"valid": True, "readiness": report}, indent=2, ensure_ascii=False))
        return 0 if report["unattended_ready"] or not args.require_all else 2
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
