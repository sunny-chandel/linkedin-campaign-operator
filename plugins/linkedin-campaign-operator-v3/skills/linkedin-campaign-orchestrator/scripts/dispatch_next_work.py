#!/usr/bin/env python3
"""Choose the next campaign task or emit a justified adaptive wait decision."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ACTIVE_STATUSES = {"pending", "recovering", "missed-recovering"}
DIRECT_TYPES = {"direct-inbound", "comment", "reply", "direct-message"}
BASE_BUDGET_TYPES = {"proactive", "soft-reciprocity"}


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False) + "\n")


def active_stage_debt(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    stages = ledger.get("stages", [])
    if not isinstance(stages, list):
        raise ValueError("stage-ledger.json stages must be an array")
    return [
        stage
        for stage in stages
        if isinstance(stage, dict)
        and stage.get("status") in {"pending", "recovering", "missed-recovering"}
    ]


def task_is_eligible(
    task: dict[str, Any],
    *,
    linkedin_lane: str,
    offline_lane: str,
    base_used: int,
    base_ceiling: int,
    posts_published: int,
    packages_ready: int,
) -> tuple[bool, str | None]:
    if task.get("status") not in ACTIVE_STATUSES or task.get("ready") is not True:
        return False, "not-ready"
    requires_linkedin = task.get("requires_linkedin") is True or task.get("lane") == "linkedin"
    if requires_linkedin and linkedin_lane == "blocked":
        return False, "linkedin-lane-blocked"
    if not requires_linkedin and offline_lane == "blocked":
        return False, "offline-lane-blocked"
    task_type = str(task.get("task_type", ""))
    action_lane = str(task.get("action_lane", ""))
    if (task_type in BASE_BUDGET_TYPES or action_lane in BASE_BUDGET_TYPES) and base_used >= base_ceiling:
        return False, "base-daily-ceiling"
    if task_type == "publication-opportunity" and posts_published >= 2:
        return False, "daily-publications-complete"
    if task_type == "two-package-production" and packages_ready >= 2:
        return False, "two-packages-ready"
    return True, None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state_dir", type=Path)
    parser.add_argument("--now", help="ISO timestamp used in deterministic tests")
    parser.add_argument("--record", action="store_true", help="append the decision to schedule-decisions.jsonl")
    args = parser.parse_args()

    state_dir = args.state_dir.expanduser().resolve()
    try:
        state = load_object(state_dir / "campaign-state.json")
        config = load_object(state_dir / "campaign-config.json")
        queue = load_object(state_dir / "work-queue.json")
        ledger = load_object(state_dir / "stage-ledger.json")
        now = args.now or datetime.now(timezone.utc).isoformat()
        if state.get("hard_blocker"):
            blocker_items = queue.get("items", [])
            if not isinstance(blocker_items, list):
                raise ValueError("work-queue.json items must be an array")
            blocker_unfinished = sum(
                1
                for item in blocker_items
                if isinstance(item, dict) and item.get("status") in ACTIVE_STATUSES
            ) + len(active_stage_debt(ledger))
            result = {
                "valid": True,
                "decision": "blocked",
                "decided_at": now,
                "priority": 1,
                "hard_blocker": state["hard_blocker"],
                "unfinished_work_count": blocker_unfinished,
                "reason": "technical signal or identity blocker must stop external and offline execution",
            }
            if args.record:
                append_jsonl(state_dir / "schedule-decisions.jsonl", result)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0
        scaling = state.get("engagement_scaling", {})
        dispatcher = state.get("dispatcher", {})
        publishing = state.get("publishing", {})
        base_used = int(scaling.get("base_actions_used", 0))
        base_ceiling = int(scaling.get("base_daily_ceiling", 100))
        overage_allowed = config.get("fixed_rules", {}).get("direct_reply_overage_allowed") is True
        concentration = scaling.get("concentration_state", {})
        if not isinstance(concentration, dict):
            concentration = {}
        concentration_penalty = float(concentration.get("current_penalty", 0) or 0)
        if not 0 <= concentration_penalty <= 1:
            raise ValueError("concentration_state.current_penalty must be from 0 to 1")
        items = queue.get("items", [])
        if not isinstance(items, list):
            raise ValueError("work-queue.json items must be an array")
        debts = active_stage_debt(ledger)
        pending_count = sum(
            1 for item in items if isinstance(item, dict) and item.get("status") in ACTIVE_STATUSES
        ) + len(debts)

        candidates: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            if (
                item.get("status") in ACTIVE_STATUSES
                and item.get("ready") is True
                and item.get("task_type") == "publication-opportunity"
                and item.get("engagement_queue_ready") is not True
            ):
                queue_task = dict(item)
                queue_task.update(
                    {
                        "task_id": f"build-publication-queue-{item.get('task_id')}",
                        "task_type": "publication-queue-building",
                        "priority": min(int(item.get("priority", 3)), 3),
                        "source_publication_task_id": item.get("task_id"),
                    }
                )
                eligible, reason = task_is_eligible(
                    queue_task,
                    linkedin_lane=str(dispatcher.get("linkedin_lane", "ready")),
                    offline_lane=str(dispatcher.get("offline_lane", "ready")),
                    base_used=base_used,
                    base_ceiling=base_ceiling,
                    posts_published=int(publishing.get("posts_published", 0)),
                    packages_ready=int(publishing.get("packages_ready", 0)),
                )
                if eligible:
                    candidates.append(queue_task)
                else:
                    rejected.append({"task_id": item.get("task_id"), "reason": reason})
                continue
            eligible, reason = task_is_eligible(
                item,
                linkedin_lane=str(dispatcher.get("linkedin_lane", "ready")),
                offline_lane=str(dispatcher.get("offline_lane", "ready")),
                base_used=base_used,
                base_ceiling=base_ceiling,
                posts_published=int(publishing.get("posts_published", 0)),
                packages_ready=int(publishing.get("packages_ready", 0)),
            )
            if eligible:
                candidates.append(item)
            elif item.get("status") in ACTIVE_STATUSES:
                rejected.append({"task_id": item.get("task_id"), "reason": reason})

        candidate_recovery_stages = {
            item.get("stage_id")
            for item in candidates
            if item.get("task_type") == "mandatory-stage-recovery"
        }
        for debt in debts:
            if debt.get("stage_id") in candidate_recovery_stages:
                continue
            candidates.append(
                {
                    "task_id": f"recover-{debt.get('stage_id')}",
                    "task_type": "mandatory-stage-recovery",
                    "lane": "offline",
                    "priority": int(debt.get("priority", 4)),
                    "status": "pending",
                    "ready": True,
                    "requires_linkedin": False,
                    "stage_id": debt.get("stage_id"),
                }
            )

        reserve = scaling.get("adaptive_reserve", {})
        if (
            int(reserve.get("qualified_count", 0) or 0) < int(reserve.get("target_count", 0) or 0)
            and not any(item.get("task_type") == "adaptive-reserve" for item in candidates)
            and base_used < base_ceiling
            and dispatcher.get("linkedin_lane", "ready") != "blocked"
        ):
            candidates.append(
                {
                    "task_id": "replenish-adaptive-reserve",
                    "task_type": "adaptive-reserve",
                    "lane": "linkedin",
                    "priority": 6,
                    "status": "pending",
                    "ready": True,
                    "requires_linkedin": True,
                }
            )

        candidates.sort(
            key=lambda item: (
                int(item.get("priority", 99)),
                -(
                    float(item.get("opportunity_score", 0) or 0)
                    - (
                        concentration_penalty * 100
                        if item.get("task_type") in BASE_BUDGET_TYPES
                        or item.get("action_lane") in BASE_BUDGET_TYPES
                        else 0
                    )
                ),
                str(item.get("task_id", "")),
            )
        )

        if candidates:
            selected = dict(candidates[0])
            task_type = str(selected.get("task_type", ""))
            action_lane = str(selected.get("action_lane", ""))
            if task_type in DIRECT_TYPES or action_lane == "direct-inbound":
                selected["budget_class"] = (
                    "base" if base_used < base_ceiling else "direct-reply-overage"
                )
                if base_used >= base_ceiling and not overage_allowed:
                    raise ValueError("direct reply overage is disabled")
            elif task_type in BASE_BUDGET_TYPES or action_lane in BASE_BUDGET_TYPES:
                selected["budget_class"] = "base"
                selected["concentration_penalty"] = concentration_penalty
                selected["effective_opportunity_score"] = round(
                    float(selected.get("opportunity_score", 0) or 0)
                    - concentration_penalty * 100,
                    2,
                )
            result = {
                "valid": True,
                "decision": "execute",
                "decided_at": now,
                "task": selected,
                "unfinished_work_count": pending_count,
                "rejected": rejected,
                "reason": "highest-priority eligible work",
            }
        elif pending_count:
            offline_available = dispatcher.get("offline_lane", "ready") != "blocked"
            if offline_available:
                result = {
                    "valid": True,
                    "decision": "execute",
                    "decided_at": now,
                    "task": {
                        "task_id": "reconcile-work-queue",
                        "task_type": "analytics-and-investigation",
                        "lane": "offline",
                        "priority": 8,
                        "requires_linkedin": False,
                    },
                    "unfinished_work_count": pending_count,
                    "rejected": rejected,
                    "reason": "unfinished work exists but requires reconciliation or a blocked lane",
                }
            else:
                result = {
                    "valid": True,
                    "decision": "blocked",
                    "decided_at": now,
                    "unfinished_work_count": pending_count,
                    "rejected": rejected,
                    "reason": "all unfinished work is blocked and the offline lane is unavailable",
                }
        else:
            next_wake_at = dispatcher.get("next_wake_at")
            next_wake_reason = dispatcher.get("next_wake_reason")
            if next_wake_at and next_wake_reason:
                result = {
                    "valid": True,
                    "decision": "wait",
                    "decided_at": now,
                    "unfinished_work_count": 0,
                    "evidence": "validated work queue and stage ledger are empty",
                    "predicted_next_opportunity": next_wake_at,
                    "wake_trigger": next_wake_reason,
                }
            else:
                result = {
                    "valid": True,
                    "decision": "execute",
                    "decided_at": now,
                    "task": {
                        "task_id": "investigate-next-opportunity",
                        "task_type": "analytics-and-investigation",
                        "lane": "offline",
                        "priority": 8,
                        "requires_linkedin": False,
                    },
                    "unfinished_work_count": 0,
                    "reason": "waiting is invalid until an evidence-backed wake trigger exists",
                }
        if args.record:
            append_jsonl(state_dir / "schedule-decisions.jsonl", result)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
