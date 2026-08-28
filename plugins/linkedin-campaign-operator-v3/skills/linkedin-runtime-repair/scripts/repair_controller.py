#!/usr/bin/env python3
"""Persist scoped runtime repair state and deterministic recovery requests."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


CAPABILITIES = {"chrome", "claude-design", "file-upload", "computer-use", "campaign-runtime"}


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain an object")
    return value


def atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def append_event(path: Path, value: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state_dir", type=Path)
    parser.add_argument("--capability", choices=sorted(CAPABILITIES))
    parser.add_argument("--failure-evidence", type=Path)
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--result", type=Path)
    parser.add_argument("--now")
    args = parser.parse_args()
    state_dir = args.state_dir.expanduser().resolve()
    now = datetime.fromisoformat(args.now) if args.now else datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    try:
        path = state_dir / "repair-state.json"
        state = load_object(path) if path.is_file() else {
            "schema_version": "2.0",
            "status": "healthy",
            "active_repair": None,
            "history": [],
        }
        if args.result:
            result = load_object(args.result)
            active = state.get("active_repair") or {}
            active["result"] = result
            active["completed_at"] = now.isoformat()
            active["verification_required"] = True
            state["status"] = "verification-pending"
            state["active_repair"] = active
            event_type = "repair-result-recorded"
        elif args.capability:
            evidence = load_object(args.failure_evidence) if args.failure_evidence else {}
            checkpoint = load_object(args.checkpoint) if args.checkpoint else {}
            repair_id = f"repair-{args.capability}-{now.strftime('%Y%m%dT%H%M%SZ')}"
            request = {
                "repair_id": repair_id,
                "capability": args.capability,
                "detected_at": now.isoformat(),
                "failure_evidence": evidence,
                "checkpoint": checkpoint,
                "recovery_order": [
                    "current-agent-computer-use",
                    "reopen-refresh-or-rebind",
                    "rerun-specific-preflight",
                    "verify-capability",
                    "resume-original-lease",
                ],
                "repair_scope": {
                    "operations": [
                        "application-session-recovery",
                        "deterministic-campaign-state-repair",
                        "reload-current-plugin-runtime",
                    ],
                    "state_boundary": "campaign-directory",
                    "external_execution_route": "official-api-executor",
                },
                "retry_trigger": (now + timedelta(minutes=15)).isoformat(),
                "continue_unaffected_work": True,
            }
            state["status"] = "repair-pending"
            state["active_repair"] = request
            event_type = "repair-requested"
        else:
            event_type = "repair-state-read"
        state["schema_version"] = "2.0"
        state["updated_at"] = now.isoformat()
        atomic_write(path, state)
        append_event(state_dir / "repair-events.jsonl", {
            "schema_version": "2.0",
            "event_type": event_type,
            "recorded_at": now.isoformat(),
            "active_repair": state.get("active_repair"),
        })
        print(json.dumps({"valid": True, "repair_state": state}, indent=2, ensure_ascii=False))
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
