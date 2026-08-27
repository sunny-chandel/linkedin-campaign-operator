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
        recovery = state.get("opportunity_recovery", {})
        opportunities = load_object(state_dir / "engagement-opportunities.json")
        operational = load_object(state_dir / "operational-output.json")
        pipeline = load_object(state_dir / "content-pipeline.json")
        regional = load_object(state_dir / "regional-performance.json")
        repair = load_object(state_dir / "repair-state.json")
        items = queue.get("items", [])
        stages = ledger.get("stages", [])
        if not isinstance(items, list) or not isinstance(stages, list):
            raise ValueError("work queue items and stage ledger stages must be arrays")
        unfinished = [
            item for item in items
            if isinstance(item, dict) and item.get("status") in {
                "pending", "recovering", "missed-recovering", "retry-wait", "leased", "running"
            }
        ]
        analytics_debt = []
        unfinished_stages = []
        for stage in stages:
            if not isinstance(stage, dict):
                continue
            if stage.get("status") not in {"completed", "missed-closed", "superseded", "cancelled"}:
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
        action_output = operational.get("actions", {})
        post_output = operational.get("publishing", {})
        base_used = int(action_output.get("rolling_24h_actions", 0))
        base_ceiling = int(action_output.get("hard_cap", 200))
        result = {
            "valid": True,
            "posting": {
                "content_day_local": (
                    publishing.get("content_day_local") or publishing.get("content_day_ist")
                ),
                "packages_ready": int(publishing.get("packages_ready", 0)),
                "packages_required": 6,
                "rolling_inventory_ready": int(pipeline.get("inventory", {}).get("validated_unpublished", 0)),
                "topic_candidates": len(pipeline.get("topic_candidates", [])),
                "briefs": len(pipeline.get("briefs", [])),
                "rolling_24h_posts": int(post_output.get("rolling_24h_posts", 0)),
                "minimum_posts_required": 6,
                "maximum_posts_allowed": 8,
                "post_debt": int(post_output.get("debt", 6)),
                "normal_posts_published": int(publishing.get("normal_posts_published", 0)),
                "recovery_posts_published": int(publishing.get("recovery_posts_published", 0)),
                "unpublished_recovery_package": publishing.get("recovery_package"),
            },
            "engagement": {
                "rolling_24h_actions": base_used,
                "rolling_action_target": int(action_output.get("target", 160)),
                "rolling_action_cap": base_ceiling,
                "action_debt": int(action_output.get("debt", 160)),
                "remaining_capacity": max(0, base_ceiling - base_used),
                "direct_inbound_replies": int(action_output.get("direct_inbound_replies", 0)),
                "adaptive_reserve": scaling.get("adaptive_reserve", {}),
                "canonical_opportunity_records": len(opportunities.get("opportunities", [])),
                "canonical_executable_opportunities": int(opportunities.get("eligible_count", 0)),
                "opportunity_health": recovery,
            },
            "analytics_debt": {
                "count": len(analytics_debt),
                "stage_ids": analytics_debt,
            },
            "blockers": {
                "hard_blocker": state.get("hard_blocker"),
                "linkedin_lane": dispatcher.get("linkedin_lane", "ready"),
                "offline_lane": dispatcher.get("offline_lane", "ready"),
                "lane_circuits": dispatcher.get("lane_circuits", {}),
            },
            "automation": {
                "consent": state.get("automation_consent", {}),
                "browser_binding": dispatcher.get("browser_binding", {}),
                "preflight_evidence": state.get("preflight_evidence", {}),
                "runtime_continuity": state.get("runtime_continuity", {}),
                "runtime_classification": state.get("runtime_classification", {}),
                "continuation": dispatcher.get("continuation", {}),
            },
            "regional_allocation": regional.get("current_allocation", {}),
            "runtime_repair": repair,
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
