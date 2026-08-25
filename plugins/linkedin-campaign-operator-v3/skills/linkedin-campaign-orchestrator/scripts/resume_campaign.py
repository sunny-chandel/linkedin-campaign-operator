#!/usr/bin/env python3
"""Self-revive a campaign after Claude, the machine, or the browser was unavailable."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from runtime_state import (
    append_jsonl,
    atomic_write,
    current_time,
    iso_time,
    load_object,
    reconcile_runtime,
)


def reconcile_missed_stages(ledger: dict, current_day: str, now: str) -> dict:
    recovered: list[str] = []
    closed_obsolete: list[str] = []
    stages = ledger.get("stages", [])
    if not isinstance(stages, list):
        raise ValueError("stage-ledger.json stages must be an array")
    for stage in stages:
        if not isinstance(stage, dict) or stage.get("status") == "completed":
            continue
        stage_day = stage.get("content_day_local") or stage.get("content_day_ist")
        if not stage_day or stage_day >= current_day:
            continue
        stage_type = stage.get("stage_type")
        if stage_type in {"preflight", "publication", "content-production"}:
            stage["status"] = "missed-closed"
            stage["closed_at"] = now
            stage["closure_reason"] = "obsolete-time-bound-stage-after-downtime"
            closed_obsolete.append(str(stage.get("stage_id")))
        else:
            stage["status"] = "missed-recovering"
            stage["recovery_reason"] = "unfinished-stage-detected-after-restart"
            stage["recovered_at"] = now
            recovered.append(str(stage.get("stage_id")))
    return {"recovered_stages": recovered, "closed_obsolete_stages": closed_obsolete}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state_dir", type=Path)
    parser.add_argument("--now", help="ISO timestamp used in deterministic tests")
    parser.add_argument("--session-id", default="claude-code-session")
    args = parser.parse_args()
    state_dir = args.state_dir.expanduser().resolve()
    try:
        state = load_object(state_dir / "campaign-state.json")
        config = load_object(state_dir / "campaign-config.json")
        queue = load_object(state_dir / "work-queue.json")
        ledger = load_object(state_dir / "stage-ledger.json")
        now = current_time(args.now)
        timestamp = iso_time(now)
        report = reconcile_runtime(
            state_dir,
            state,
            config,
            queue,
            ledger,
            now,
            startup=True,
        )
        missed = reconcile_missed_stages(
            ledger,
            report["content_day"]["content_day_local"],
            timestamp,
        )
        continuity = state.setdefault("runtime_continuity", {})
        continuity["active_session_id"] = args.session_id
        continuity["recovery_status"] = "ready-to-dispatch" if report["consent_valid"] else "consent-required"
        continuity["last_recovery_report"].update(missed)
        state["lifecycle_state"] = (
            "running"
            if report["consent_valid"] and state.get("lifecycle_state") not in {"completed", "user-stopped"}
            else state.get("lifecycle_state", "ready")
        )
        atomic_write(state_dir / "campaign-state.json", state)
        atomic_write(state_dir / "work-queue.json", queue)
        atomic_write(state_dir / "stage-ledger.json", ledger)
        event = {
            "event": "session-self-revival",
            "session_id": args.session_id,
            "recorded_at": timestamp,
            "consent_valid": report["consent_valid"],
            "content_day": report["content_day"],
            "expired_leases": report["task_lifecycle"]["expired_leases"],
            "missed_tasks": report["task_lifecycle"]["missed_tasks"],
            **missed,
        }
        append_jsonl(state_dir / "recovery-events.jsonl", event)
        result = {
            "valid": True,
            "self_revived": report["consent_valid"],
            "consent_valid": report["consent_valid"],
            "consent_reason": report["consent_reason"],
            "content_day": report["content_day"],
            "expired_leases": report["task_lifecycle"]["expired_leases"],
            "missed_tasks": report["task_lifecycle"]["missed_tasks"],
            **missed,
            "next_step": (
                "run audit_pipeline.py --write, then dispatch_next_work.py --record and execute without asking"
                if report["consent_valid"]
                else "ask the recognized owner for the single automation consent, store it, then rerun self-revival"
            ),
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
