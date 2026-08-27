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
PACKAGE_STAGES = {
    "research_brief",
    "claim_verification",
    "caption",
    "asset",
    "watermark",
    "validation",
    "publication_decision",
}
ANALYTICS_CHECKPOINTS = {30, 120, 360, 1440}


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
        pipeline_path = state_dir / "content-pipeline.json"
        pipeline_reports: list[dict[str, Any]] = []
        if pipeline_path.is_file():
            pipeline = load_object(pipeline_path)
            packages = pipeline.get("packages", [])
            schedules = pipeline.get("analytics_schedule", [])
            if not isinstance(packages, list) or not isinstance(schedules, list):
                raise ValueError("content-pipeline packages and analytics_schedule must be arrays")
            current_time = parse_time(now)
            for package in packages:
                if not isinstance(package, dict):
                    continue
                package_id = str(package.get("package_id") or "unknown")
                status = package.get("status")
                stage_map = package.get("stages", {})
                missing_package_stages = sorted(
                    stage for stage in PACKAGE_STAGES
                    if not isinstance(stage_map, dict) or stage_map.get(stage) is not True
                )
                if status in {"ready", "validated"} and missing_package_stages:
                    package["status"] = "needs-v6-revalidation"
                    invalid_claims += 1
                    recovery_tasks.append({
                        "task_id": f"replenish-{package_id}",
                        "task_type": "six-package-replenishment",
                        "lane": "offline",
                        "priority": 5,
                        "status": "pending",
                        "ready": True,
                        "requires_linkedin": False,
                        "package_id": package_id,
                        "missing_package_stages": missing_package_stages,
                    })
                expected_checkpoints = {
                    int(item.get("checkpoint_minutes"))
                    for item in schedules
                    if isinstance(item, dict) and item.get("post_id") in {package_id, package.get("post_id")}
                    and isinstance(item.get("checkpoint_minutes"), (int, float))
                }
                if (
                    status == "published"
                    and package.get("analytics_contract") != "legacy-preserved"
                    and expected_checkpoints != ANALYTICS_CHECKPOINTS
                ):
                    invalid_claims += 1
                    recovery_tasks.append({
                        "task_id": f"schedule-analytics-{package_id}",
                        "task_type": "scheduled-analytics-snapshot",
                        "lane": "offline",
                        "priority": 4,
                        "status": "pending",
                        "ready": True,
                        "requires_linkedin": False,
                        "post_id": package.get("post_id") or package_id,
                        "missing_checkpoints": sorted(ANALYTICS_CHECKPOINTS - expected_checkpoints),
                    })
                pipeline_reports.append({
                    "package_id": package_id,
                    "status": package.get("status"),
                    "missing_package_stages": missing_package_stages,
                    "analytics_checkpoints": sorted(expected_checkpoints),
                })
            for snapshot in schedules:
                if not isinstance(snapshot, dict) or snapshot.get("status") == "completed":
                    continue
                due_at = parse_time(snapshot.get("due_at"))
                if due_at is None or current_time is None or due_at > current_time:
                    continue
                post_id = str(snapshot.get("post_id") or "unknown")
                minutes = int(snapshot.get("checkpoint_minutes", 0) or 0)
                recovery_tasks.append({
                    "task_id": f"analytics-{post_id}-{minutes}",
                    "task_type": "scheduled-analytics-snapshot",
                    "lane": "linkedin",
                    "priority": 4,
                    "status": "pending",
                    "ready": True,
                    "requires_linkedin": True,
                    "post_id": post_id,
                    "checkpoint_minutes": minutes,
                    "required_completion_artifacts": [
                        "snapshot", "learning", "decision", "next_measurement_trigger"
                    ],
                })
            if args.write:
                atomic_write(pipeline_path, pipeline)
        ledger["updated_at"] = now
        if args.write:
            atomic_write(ledger_path, ledger)
            queue_path = state_dir / "work-queue.json"
            queue = load_object(queue_path)
            queue_items = queue.setdefault("items", [])
            if not isinstance(queue_items, list):
                raise ValueError("work-queue.json items must be an array")
            for task in recovery_tasks:
                existing = next(
                    (
                        item for item in queue_items
                        if isinstance(item, dict) and item.get("task_id") == task.get("task_id")
                    ),
                    None,
                )
                if existing is None:
                    queue_items.append(task)
                elif existing.get("status") in {"completed", "cancelled", "expired", "superseded"}:
                    continue
                else:
                    existing.update({key: value for key, value in task.items() if key != "status"})
            queue["updated_at"] = now
            atomic_write(queue_path, queue)
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
            "content_pipeline": pipeline_reports,
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
