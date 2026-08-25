#!/usr/bin/env python3
"""Report posting, engagement, analytics debt, blockers, and true idle state."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def last_jsonl(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    for line in reversed(path.read_text(encoding="utf-8").splitlines()):
        if line.strip():
            value = json.loads(line)
            return value if isinstance(value, dict) else None
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state_dir", type=Path)
    args = parser.parse_args()
    state_dir = args.state_dir.expanduser().resolve()
    try:
        state = load_object(state_dir / "campaign-state.json")
        queue = load_object(state_dir / "work-queue.json")
        ledger = load_object(state_dir / "stage-ledger.json")
        publishing = state.get("publishing", {})
        scaling = state.get("engagement_scaling", {})
        dispatcher = state.get("dispatcher", {})
        items = queue.get("items", [])
        stages = ledger.get("stages", [])
        if not isinstance(items, list) or not isinstance(stages, list):
            raise ValueError("work queue items and stage ledger stages must be arrays")
        unfinished = [
            item for item in items
            if isinstance(item, dict) and item.get("status") in {"pending", "recovering", "missed-recovering"}
        ]
        analytics_debt = []
        unfinished_stages = []
        for stage in stages:
            if not isinstance(stage, dict):
                continue
            if stage.get("status") != "completed":
                unfinished_stages.append(stage.get("stage_id"))
            if stage.get("stage_type") != "analytics":
                continue
            complete = (
                stage.get("status") == "completed"
                and stage.get("learning_recorded") is True
                and stage.get("learning_status") in {"provisional", "validated"}
                and stage.get("experiment_outcome") in {"experiment-registered", "no-change"}
                and bool(stage.get("next_measurement_trigger"))
            )
            if not complete:
                analytics_debt.append(stage.get("stage_id"))
        last_decision = last_jsonl(state_dir / "schedule-decisions.jsonl")
        true_idle = bool(
            not unfinished
            and not unfinished_stages
            and not analytics_debt
            and last_decision
            and last_decision.get("decision") == "wait"
            and last_decision.get("unfinished_work_count") == 0
            and last_decision.get("predicted_next_opportunity")
            and last_decision.get("wake_trigger")
        )
        base_used = int(scaling.get("base_actions_used", 0))
        base_ceiling = int(scaling.get("base_daily_ceiling", 100))
        result = {
            "valid": True,
            "posting": {
                "content_day_ist": publishing.get("content_day_ist"),
                "packages_ready": int(publishing.get("packages_ready", 0)),
                "packages_required": int(publishing.get("packages_required", 2)),
                "posts_published": int(publishing.get("posts_published", 0)),
                "posts_required": 2,
            },
            "engagement": {
                "base_actions_used": base_used,
                "base_daily_ceiling": base_ceiling,
                "base_remaining": max(0, base_ceiling - base_used),
                "direct_reply_overage": int(scaling.get("direct_reply_overage", 0)),
            },
            "analytics_debt": {
                "count": len(analytics_debt),
                "stage_ids": analytics_debt,
            },
            "blockers": {
                "hard_blocker": state.get("hard_blocker"),
                "linkedin_lane": dispatcher.get("linkedin_lane", "ready"),
                "offline_lane": dispatcher.get("offline_lane", "ready"),
            },
            "unfinished_work_count": len(unfinished),
            "unfinished_stage_count": len(unfinished_stages),
            "unfinished_stage_ids": unfinished_stages,
            "true_idle": true_idle,
            "last_schedule_decision": last_decision,
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
