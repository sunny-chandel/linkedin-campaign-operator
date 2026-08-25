#!/usr/bin/env python3
"""Audit mandatory stage completion and emit automatic recovery tasks."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runtime_state import parse_time


ANALYTICS_OUTCOMES = {"experiment-registered", "no-change"}
ANALYTICS_LEARNING_STATUSES = {"provisional", "validated"}
TERMINAL_STAGE_STATUSES = {"completed", "missed-closed", "superseded", "cancelled"}


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def atomic_write(path: Path, value: dict[str, Any]) -> None:
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


def artifact_valid(state_dir: Path, relative: str) -> bool:
    path = state_dir / relative
    return path.is_file() and path.stat().st_size > 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state_dir", type=Path)
    parser.add_argument("--now")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()

    state_dir = args.state_dir.expanduser().resolve()
    ledger_path = state_dir / "stage-ledger.json"
    try:
        ledger = load_object(ledger_path)
        stages = ledger.get("stages", [])
        if not isinstance(stages, list):
            raise ValueError("stage-ledger.json stages must be an array")
        now = args.now or datetime.now(timezone.utc).isoformat()
        reports: list[dict[str, Any]] = []
        recovery_tasks: list[dict[str, Any]] = []
        invalid_claims = 0
        for position, stage in enumerate(stages):
            if not isinstance(stage, dict):
                raise ValueError(f"stage-ledger.json stages[{position}] must be an object")
            stage_id = stage.get("stage_id")
            required = stage.get("required_artifacts", [])
            if not isinstance(stage_id, str) or not stage_id:
                raise ValueError(f"stage-ledger.json stages[{position}].stage_id must be set")
            if not isinstance(required, list) or not all(isinstance(item, str) for item in required):
                raise ValueError(f"{stage_id}.required_artifacts must be an array of paths")
            missing = [path for path in required if not artifact_valid(state_dir, path)]
            analytics_errors: list[str] = []
            if stage.get("stage_type") == "analytics":
                if stage.get("learning_recorded") is not True:
                    analytics_errors.append("learning_recorded")
                if stage.get("learning_status") not in ANALYTICS_LEARNING_STATUSES:
                    analytics_errors.append("learning_status")
                if stage.get("experiment_outcome") not in ANALYTICS_OUTCOMES:
                    analytics_errors.append("experiment_outcome")
                if not stage.get("next_measurement_trigger"):
                    analytics_errors.append("next_measurement_trigger")
            if stage.get("stage_type") == "publication" and stage.get("status") == "completed":
                if stage.get("evidence_recorded") is not True:
                    analytics_errors.append("publication_evidence_recorded")
            valid_completion = not missing and not analytics_errors
            claimed_complete = stage.get("status") == "completed"
            if claimed_complete and not valid_completion:
                stage["status"] = "missed-recovering"
                invalid_claims += 1
            due_at = parse_time(stage.get("due_at"))
            current_time = parse_time(now)
            analytics_due = (
                stage.get("stage_type") == "analytics"
                and stage.get("status") != "completed"
                and (
                    stage.get("status") in {"recovering", "missed-recovering"}
                    or (due_at is not None and current_time is not None and due_at <= current_time)
                )
            )
            if analytics_due and (missing or analytics_errors):
                stage["status"] = "missed-recovering"
            if stage.get("status") == "missed-recovering" or (claimed_complete and not valid_completion):
                recovery_tasks.append(
                    {
                        "task_id": f"recover-{stage_id}",
                        "task_type": "mandatory-stage-recovery",
                        "lane": "offline",
                        "priority": 4,
                        "status": "pending",
                        "ready": True,
                        "requires_linkedin": False,
                        "stage_id": stage_id,
                        "missing_artifacts": missing,
                        "missing_analytics_fields": analytics_errors,
                    }
                )
            reports.append(
                {
                    "stage_id": stage_id,
                    "status": stage.get("status"),
                    "valid_completion": valid_completion,
                    "missing_artifacts": missing,
                    "missing_analytics_fields": analytics_errors,
                }
            )
        ledger["updated_at"] = now
        if args.write:
            atomic_write(ledger_path, ledger)
        unfinished_stage_count = sum(
            1 for report in reports if report["status"] not in TERMINAL_STAGE_STATUSES
        )
        result = {
            "valid": invalid_claims == 0,
            "audited_at": now,
            "stage_count": len(stages),
            "invalid_completion_claims": invalid_claims,
            "unfinished_stage_count": unfinished_stage_count,
            "stages": reports,
            "recovery_tasks": recovery_tasks,
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        if args.require_complete and unfinished_stage_count:
            return 1
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
