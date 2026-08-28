#!/usr/bin/env python3
"""Run and verify the LinkedIn official-API outbox as a background service."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from automation_readiness import readiness_report


SCRIPT_DIR = Path(__file__).resolve().parent
EXECUTOR_SCRIPT = SCRIPT_DIR / "execute_external_action.py"
RUNTIME_SCRIPT = SCRIPT_DIR / "runtime_control.py"
OUTBOX_STATUSES = ("pending", "running", "verified", "deferred", "ambiguous", "failed")


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def atomic_write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(dict(value), handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def run_json(arguments: list[str]) -> tuple[int, dict[str, Any]]:
    completed = subprocess.run(arguments, check=False, capture_output=True, text=True)
    raw = completed.stdout.strip() or completed.stderr.strip()
    try:
        payload = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        payload = {"valid": False, "error": "subprocess returned non-JSON output"}
    return completed.returncode, payload if isinstance(payload, dict) else {"value": payload}


def move_with_result(
    state_dir: Path,
    running_path: Path,
    status: str,
    action: dict[str, Any],
    result: Mapping[str, Any],
) -> Path:
    action["daemon_result"] = dict(result)
    action["daemon_status"] = status
    action["daemon_recorded_at"] = datetime.now(timezone.utc).isoformat()
    atomic_write(running_path, action)
    destination = state_dir / "external-action-outbox" / status / running_path.name
    os.replace(running_path, destination)
    return destination


def complete_publication(
    state_dir: Path,
    action: Mapping[str, Any],
    event: Mapping[str, Any],
) -> dict[str, Any]:
    resource_id = event.get("resource_id")
    if not isinstance(resource_id, str) or not resource_id.startswith("urn:li:"):
        raise ValueError("verified publication result is missing a LinkedIn post URN")
    payload = {
        "verified": True,
        "region": action.get("region"),
        "post_id": resource_id,
        "post_url": f"https://www.linkedin.com/feed/update/{resource_id}/",
        "published_at": event.get("attempted_at"),
        "package_id": action.get("package_id"),
    }
    code, result = run_json(
        [
            sys.executable,
            str(RUNTIME_SCRIPT),
            str(state_dir),
            "task-event",
            "--task-id",
            str(action["source_task_id"]),
            "--event",
            "complete",
            "--payload",
            json.dumps(payload),
        ]
    )
    if code:
        raise ValueError(f"publication evidence persistence failed: {result.get('error')}")
    return result


def verified_group_actions(state_dir: Path, task_id: str) -> list[dict[str, Any]]:
    verified_dir = state_dir / "external-action-outbox" / "verified"
    records: list[dict[str, Any]] = []
    for path in sorted(verified_dir.glob("*.json")):
        try:
            action = load_object(path)
        except (OSError, json.JSONDecodeError, ValueError):
            continue
        if action.get("source_task_id") == task_id:
            records.append(action)
    return records


def complete_non_publication(
    state_dir: Path,
    action: Mapping[str, Any],
    event: Mapping[str, Any],
) -> dict[str, Any]:
    task_id = str(action["source_task_id"])
    queue = load_object(state_dir / "work-queue.json")
    task = next(
        (
            item
            for item in queue.get("items", [])
            if isinstance(item, dict) and item.get("task_id") == task_id
        ),
        None,
    )
    if task is None:
        raise ValueError(f"verified action refers to unknown task: {task_id}")
    if task.get("task_type") in {"engagement-burst", "engagement-burst-execution"}:
        records = verified_group_actions(state_dir, task_id) + [dict(action)]
        by_key = {
            str(record.get("idempotency_key")): record
            for record in records
            if record.get("idempotency_key")
        }
        expected = int(action.get("group_expected", task.get("action_count", 1)) or 1)
        if len(by_key) < expected:
            return {"valid": True, "group_complete": False, "verified": len(by_key), "expected": expected}
        candidate_ids = [
            str(record.get("candidate_id"))
            for record in by_key.values()
            if record.get("candidate_id")
        ]
        code, result = run_json(
            [
                sys.executable,
                str(RUNTIME_SCRIPT),
                str(state_dir),
                "burst-complete",
                "--task-id",
                task_id,
                "--executed-candidate-ids",
                json.dumps(candidate_ids),
            ]
        )
    else:
        code, result = run_json(
            [
                sys.executable,
                str(RUNTIME_SCRIPT),
                str(state_dir),
                "task-event",
                "--task-id",
                task_id,
                "--event",
                "complete",
                "--payload",
                json.dumps(
                    {
                        "verified": True,
                        "resource_id": event.get("resource_id"),
                        "action_class": action.get("action_class"),
                    }
                ),
            ]
        )
    if code:
        raise ValueError(f"task completion persistence failed: {result.get('error')}")
    return result


def record_ambiguous(state_dir: Path, action: Mapping[str, Any], result: Mapping[str, Any]) -> None:
    run_json(
        [
            sys.executable,
            str(RUNTIME_SCRIPT),
            str(state_dir),
            "task-event",
            "--task-id",
            str(action["source_task_id"]),
            "--event",
            "checkpoint",
            "--payload",
            json.dumps(
                {
                    "external_outcome": "ambiguous",
                    "idempotency_key": action.get("idempotency_key"),
                    "daemon_result": dict(result),
                    "automatic_retry_forbidden": True,
                }
            ),
        ]
    )


def process_one(state_dir: Path, pending_path: Path) -> dict[str, Any]:
    running_path = state_dir / "external-action-outbox" / "running" / pending_path.name
    try:
        os.replace(pending_path, running_path)
    except FileNotFoundError:
        return {"valid": True, "decision": "already-claimed"}
    action = load_object(running_path)
    code, result = run_json(
        [sys.executable, str(EXECUTOR_SCRIPT), str(state_dir), str(running_path)]
    )
    if code == 0 and result.get("valid") is True:
        event = result.get("event", {})
        if not isinstance(event, Mapping):
            event = {}
        destination = move_with_result(state_dir, running_path, "verified", action, result)
        try:
            if action.get("action_class") == "publication":
                completion = complete_publication(state_dir, action, event)
            else:
                completion = complete_non_publication(state_dir, action, event)
        except Exception as exc:
            return {
                "valid": False,
                "decision": "verified-external-state-persistence-repair-required",
                "outbox_path": str(destination),
                "error": str(exc),
            }
        return {"valid": True, "decision": "verified", "completion": completion}
    if code == 3:
        destination = move_with_result(state_dir, running_path, "ambiguous", action, result)
        record_ambiguous(state_dir, action, result)
        return {"valid": False, "decision": "ambiguous-stop", "outbox_path": str(destination)}
    status = "deferred" if code == 2 else "failed"
    destination = move_with_result(state_dir, running_path, status, action, result)
    return {
        "valid": False,
        "decision": "deferred-until-readiness" if code == 2 else "technical-failure",
        "outbox_path": str(destination),
        "result": result,
    }


def runtime_report(state_dir: Path, **updates: Any) -> None:
    path = state_dir / "external-executor-runtime.json"
    current: dict[str, Any] = {}
    if path.is_file():
        try:
            current = load_object(path)
        except (OSError, json.JSONDecodeError, ValueError):
            current = {}
    current.update(updates)
    current["updated_at"] = datetime.now(timezone.utc).isoformat()
    current["pid"] = os.getpid()
    atomic_write(path, current)


def one_cycle(state_dir: Path) -> dict[str, Any]:
    executor = load_object(state_dir / "external-executor.json")
    config = load_object(state_dir / "campaign-config.json")
    required_values = config.get("autonomous_execution", {}).get(
        "required_action_classes", ["publication", "comment", "reply", "reaction"]
    )
    required = {str(value) for value in required_values if isinstance(value, str)}
    readiness = readiness_report(executor, required)
    if not readiness["zero_human_ready"]:
        result = {"valid": False, "decision": "readiness-blocked", "readiness": readiness}
        runtime_report(state_dir, status="blocked", last_result=result)
        return result
    pending_dir = state_dir / "external-action-outbox" / "pending"
    pending = sorted(pending_dir.glob("*.json"))
    results = []
    for path in pending:
        result = process_one(state_dir, path)
        results.append(result)
        if result.get("decision") == "ambiguous-stop":
            break
    report = {
        "valid": all(result.get("valid") for result in results),
        "decision": "processed" if results else "idle",
        "processed": len(results),
        "results": results,
    }
    runtime_report(state_dir, status=report["decision"], last_result=report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state_dir", type=Path)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--poll-seconds", type=int, default=15)
    args = parser.parse_args()
    state_dir = args.state_dir.expanduser().resolve()
    for status in OUTBOX_STATUSES:
        (state_dir / "external-action-outbox" / status).mkdir(parents=True, exist_ok=True)
    lock_path = state_dir / "external-executor.lock"
    with lock_path.open("a+") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(json.dumps({"valid": False, "error": "executor-daemon-already-running"}))
            return 4
        while True:
            try:
                report = one_cycle(state_dir)
            except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
                report = {"valid": False, "decision": "runtime-error", "error": str(exc)}
                runtime_report(state_dir, status="error", last_result=report)
            if args.once:
                print(json.dumps(report, indent=2, ensure_ascii=False))
                return 0 if report.get("valid") or report.get("decision") == "idle" else 2
            time.sleep(max(1, min(args.poll_seconds, 300)))


if __name__ == "__main__":
    raise SystemExit(main())
