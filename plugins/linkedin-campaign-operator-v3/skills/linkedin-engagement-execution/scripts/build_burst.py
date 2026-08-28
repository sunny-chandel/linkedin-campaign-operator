#!/usr/bin/env python3
"""Build a burst from canonical eligible opportunities and rolling capacity."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ORCHESTRATOR_SCRIPTS = Path(__file__).resolve().parents[2] / "linkedin-campaign-orchestrator" / "scripts"
sys.path.insert(0, str(ORCHESTRATOR_SCRIPTS))
from opportunity_recovery import eligible_opportunities  # noqa: E402
from service_readiness import task_readiness  # noqa: E402

from rolling_output import ACTION_CAP, parse_time, refresh_output  # noqa: E402


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain an object")
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state_dir", type=Path)
    parser.add_argument("--now")
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()
    state_dir = args.state_dir.expanduser().resolve()
    now = parse_time(args.now) if args.now else datetime.now(timezone.utc)
    if now is None:
        parser.error("--now must be an ISO timestamp")
    try:
        state = load_object(state_dir / "campaign-state.json")
        config = load_object(state_dir / "campaign-config.json")
        document = load_object(state_dir / "engagement-opportunities.json")
        executor = load_object(state_dir / "external-executor.json")
        output = refresh_output(state_dir, now, write=args.record)
        capacity = max(0, ACTION_CAP - int(output["actions"]["rolling_24h_actions"]))
        eligible = [
            item
            for item in eligible_opportunities(document, state, config, now)
            if task_readiness(
                {"task_type": "engagement-burst-execution", "actions": [item]},
                executor,
            )["unattended_ready"]
        ]
        direct = [item for item in eligible if item.get("lane") == "direct-inbound"]
        counted = [item for item in eligible if item.get("lane") != "direct-inbound"][: min(10, capacity)]
        selected = (direct + counted)[:10]
        task = None
        if selected:
            task = {
                "task_id": f"engagement-burst-{now.strftime('%Y%m%dT%H%M%SZ')}",
                "task_type": "engagement-burst-execution",
                "lane": "linkedin",
                "priority": 3,
                "status": "pending",
                "ready": True,
                "requires_linkedin": True,
                "created_at": now.isoformat(),
                "actions": selected,
                "action_count": len(selected),
                "rolling_capacity_before": capacity,
                "idempotency_key": "burst:" + ":".join(str(item.get("opportunity_id") or item.get("candidate_id")) for item in selected),
            }
        if args.record and task is not None:
            queue_path = state_dir / "work-queue.json"
            queue = load_object(queue_path)
            items = queue.setdefault("items", [])
            if not any(item.get("idempotency_key") == task["idempotency_key"] and item.get("status") not in {"completed", "cancelled", "expired"} for item in items if isinstance(item, dict)):
                items.append(task)
            queue["updated_at"] = now.isoformat()
            atomic_write(queue_path, queue)
        print(json.dumps({
            "valid": True,
            "decision": "engagement-burst" if task else "no-eligible-burst",
            "task": task,
            "eligible_count": len(eligible),
            "rolling_capacity": capacity,
        }, indent=2, ensure_ascii=False))
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
