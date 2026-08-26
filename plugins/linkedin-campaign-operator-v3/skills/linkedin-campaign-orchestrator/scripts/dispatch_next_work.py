#!/usr/bin/env python3
"""Choose the next campaign task or emit a justified adaptive wait decision."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from runtime_state import (
    current_time,
    iso_time,
    lease_task,
    parse_time,
    reconcile_runtime,
)


ACTIVE_STATUSES = {"pending", "recovering", "missed-recovering"}
UNFINISHED_STATUSES = ACTIVE_STATUSES | {"retry-wait", "leased", "running"}
DIRECT_TYPES = {"direct-inbound", "comment", "reply", "direct-message"}
BASE_BUDGET_TYPES = {"proactive", "soft-reciprocity"}
PRIORITY_BY_TYPE = {
    "preflight": 1,
    "lane-recovery-probe": 1,
    "direct-inbound": 1,
    "comment": 1,
    "reply": 1,
    "direct-message": 1,
    "publication-opportunity": 2,
    "publication-queue-building": 2,
    "mandatory-stage-recovery": 3,
    "soft-reciprocity": 4,
    "two-package-production": 5,
    "adaptive-reserve": 6,
    "analytics-and-investigation": 8,
}
STARVATION_EXEMPT_TYPES = {
    "preflight",
    "lane-recovery-probe",
    "direct-inbound",
    "comment",
    "reply",
    "direct-message",
    "publication-opportunity",
    "publication-queue-building",
    "mandatory-stage-recovery",
}


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False) + "\n")


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


def local_day(timestamp: str, timezone_name: str) -> str:
    normalized = timestamp[:-1] + "+00:00" if timestamp.endswith("Z") else timestamp
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(ZoneInfo(timezone_name)).date().isoformat()


def record_decision(state_dir: Path, state: dict[str, Any], result: dict[str, Any]) -> None:
    append_jsonl(state_dir / "schedule-decisions.jsonl", result)
    dispatcher = state.setdefault("dispatcher", {})
    dispatcher["last_decision_at"] = result.get("decided_at")
    dispatcher["unfinished_work_count"] = int(result.get("unfinished_work_count", 0) or 0)
    dispatcher["current_task_id"] = (
        result.get("task", {}).get("task_id") if isinstance(result.get("task"), dict) else None
    )
    if result.get("decision") == "execute" and isinstance(result.get("task"), dict):
        selected_type = result["task"].get("task_type")
        previous_type = dispatcher.get("last_selected_task_type")
        dispatcher["consecutive_same_task_type"] = (
            int(dispatcher.get("consecutive_same_task_type", 0) or 0) + 1
            if previous_type == selected_type
            else 1
        )
        dispatcher["last_selected_task_type"] = selected_type
        state["current_stage"] = selected_type
        if state.get("lifecycle_state") not in {"completed", "user-stopped"}:
            state["lifecycle_state"] = "running"
    if result.get("decision") == "wait":
        dispatcher["next_wake_at"] = result.get("predicted_next_opportunity")
        dispatcher["next_wake_reason"] = result.get("wake_trigger")
        requested = result.get("continuation", {})
        continuation = dispatcher.setdefault("continuation", {})
        if isinstance(requested, dict):
            continuation.update(requested)
        continuation["status"] = "wake-required"
        continuation["requested_at"] = result.get("decided_at")
    elif result.get("decision") == "execute":
        dispatcher["next_wake_at"] = None
        dispatcher["next_wake_reason"] = None
        continuation = dispatcher.setdefault("continuation", {})
        continuation["status"] = "active"
        continuation["last_woke_at"] = result.get("decided_at")
    state["updated_at"] = result.get("decided_at")
    atomic_write(state_dir / "campaign-state.json", state)


def active_stage_debt(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    stages = ledger.get("stages", [])
    if not isinstance(stages, list):
        raise ValueError("stage-ledger.json stages must be an array")
    return [
        stage
        for stage in stages
        if isinstance(stage, dict)
        and stage.get("status") in {"recovering", "missed-recovering"}
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
    if requires_linkedin and linkedin_lane != "ready" and task.get("task_type") != "lane-recovery-probe":
        return False, f"linkedin-lane-{linkedin_lane}"
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


def automatic_continuation(
    state_dir: Path,
    config: dict[str, Any],
    wake_at: str,
    wake_trigger: str,
) -> dict[str, Any]:
    configured = config.get("adaptive_dispatch", {}).get("continuation", {})
    if not isinstance(configured, dict):
        configured = {}
    adapters = configured.get(
        "host_adapter_priority",
        ["host-native-scheduled-wake", "host-native-heartbeat", "dynamic-session-loop"],
    )
    if not isinstance(adapters, list) or not adapters:
        adapters = ["host-native-scheduled-wake", "host-native-heartbeat", "dynamic-session-loop"]
    campaign_id = str(config.get("campaign_id") or state_dir.name)
    return {
        "mode": "automatic",
        "owner_input_required": False,
        "action": "arm-or-update-single-host-wake",
        "dedupe_key": f"linkedin-campaign-continuation:{campaign_id}",
        "host_adapter_priority": [str(adapter) for adapter in adapters],
        "next_wake_at": wake_at,
        "wake_trigger": wake_trigger,
        "state_dir": str(state_dir),
        "resume_instruction": (
            "Resume this campaign from durable state, run self-revival, audit, dispatch, "
            "and execute the returned work autonomously."
        ),
    }


def future_wake_candidates(
    items: list[dict[str, Any]],
    dispatcher: dict[str, Any],
    now_dt: datetime,
) -> list[dict[str, Any]]:
    wakes: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        status = item.get("status")
        next_eligible = parse_time(item.get("next_eligible_at"))
        due_at = parse_time(item.get("due_at"))
        if status == "retry-wait" and next_eligible and next_eligible > now_dt:
            wakes.append(
                {
                    "at": next_eligible,
                    "trigger": f"retry-wait-ready:{item.get('task_id')}",
                    "task_id": item.get("task_id"),
                }
            )
        elif status in UNFINISHED_STATUSES and item.get("ready") is False and due_at and due_at > now_dt:
            wakes.append(
                {
                    "at": due_at,
                    "trigger": f"task-due:{item.get('task_id')}",
                    "task_id": item.get("task_id"),
                }
            )
    circuits = dispatcher.get("lane_circuits", {})
    if isinstance(circuits, dict):
        for lane, circuit in circuits.items():
            if not isinstance(circuit, dict):
                continue
            probe_at = parse_time(circuit.get("next_probe_at"))
            if probe_at and probe_at > now_dt:
                wakes.append(
                    {
                        "at": probe_at,
                        "trigger": f"lane-recovery-probe:{lane}",
                        "task_id": None,
                    }
                )
    recorded_at = parse_time(dispatcher.get("next_wake_at"))
    if recorded_at and recorded_at > now_dt and dispatcher.get("next_wake_reason"):
        wakes.append(
            {
                "at": recorded_at,
                "trigger": str(dispatcher["next_wake_reason"]),
                "task_id": None,
            }
        )
    return sorted(wakes, key=lambda wake: (wake["at"], str(wake["trigger"])))


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
        now_dt = current_time(args.now)
        now = iso_time(now_dt)
        reconciliation = reconcile_runtime(
            state_dir,
            state,
            config,
            queue,
            ledger,
            now_dt,
            startup=False,
        )
        dispatcher = state.get("dispatcher", {})
        global_hard_blocker = state.get("hard_blocker") and dispatcher.get("offline_lane") == "blocked"
        if global_hard_blocker:
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
                "reason": "required technical dependency is unavailable and neither work lane can advance",
            }
            if args.record:
                record_decision(state_dir, state, result)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0
        if state.get("hard_blocker"):
            dispatcher["linkedin_lane"] = "blocked"
        if not reconciliation["consent_valid"]:
            result = {
                "valid": True,
                "decision": "consent-required",
                "decided_at": now,
                "priority": 0,
                "reason": reconciliation["consent_reason"],
                "prompt": "I will run your configured LinkedIn operating system in fully automated mode, perform pre-flight checks, store this campaign-lifetime consent, recover unfinished work after restarts, and stop asking for routine approvals. Start?",
                "unfinished_work_count": 0,
            }
            if args.record:
                atomic_write(state_dir / "work-queue.json", queue)
                atomic_write(state_dir / "stage-ledger.json", ledger)
                record_decision(state_dir, state, result)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0
        scaling = state.get("engagement_scaling", {})
        publishing = state.get("publishing", {})
        current_budget_day = reconciliation["content_day"]["content_day_local"]
        budget_day_reset = reconciliation["budget_day_reset"]
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
            1 for item in items if isinstance(item, dict) and item.get("status") in UNFINISHED_STATUSES
        ) + len(debts)
        future_wakes = future_wake_candidates(items, dispatcher, now_dt)
        deferred_task_ids = {
            wake.get("task_id") for wake in future_wakes if wake.get("task_id")
        }
        reconcilable_count = sum(
            1
            for item in items
            if isinstance(item, dict)
            and item.get("status") in UNFINISHED_STATUSES
            and item.get("task_id") not in deferred_task_ids
        ) + len(debts)

        candidates: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        existing_task_ids = {
            item.get("task_id") for item in items if isinstance(item, dict) and item.get("task_id")
        }
        for item in items:
            if not isinstance(item, dict):
                continue
            if (
                item.get("status") in ACTIVE_STATUSES
                and item.get("ready") is True
                and item.get("task_type") == "publication-opportunity"
                and item.get("engagement_queue_ready") is not True
            ):
                derived_task_id = f"build-publication-queue-{item.get('task_id')}"
                if derived_task_id in existing_task_ids:
                    continue
                queue_task = dict(item)
                queue_task.update(
                    {
                        "task_id": derived_task_id,
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

        lane_circuit = dispatcher.get("lane_circuits", {}).get("linkedin", {})
        next_probe = parse_time(lane_circuit.get("next_probe_at")) if isinstance(lane_circuit, dict) else None
        if (
            dispatcher.get("linkedin_lane") == "recovering"
            and next_probe is not None
            and next_probe <= now_dt
        ):
            candidates.append(
                {
                    "task_id": f"probe-linkedin-{current_budget_day}",
                    "task_type": "lane-recovery-probe",
                    "lane": "linkedin",
                    "priority": 1,
                    "status": "pending",
                    "ready": True,
                    "requires_linkedin": True,
                    "idempotency_key": f"linkedin-probe:{lane_circuit.get('next_probe_at')}",
                }
            )

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
            and not any(
                isinstance(item, dict)
                and item.get("task_type") == "adaptive-reserve"
                and item.get("status") in UNFINISHED_STATUSES
                for item in items
            )
            and base_used < base_ceiling
            and dispatcher.get("linkedin_lane", "ready") == "ready"
        ):
            reserve_history = reserve.get("pass_history", [])
            pass_number = len(reserve_history if isinstance(reserve_history, list) else []) + 1
            candidates.append(
                {
                    "task_id": f"replenish-adaptive-reserve-{current_budget_day}-pass-{pass_number}",
                    "task_type": "adaptive-reserve",
                    "lane": "linkedin",
                    "priority": 6,
                    "status": "pending",
                    "ready": True,
                    "requires_linkedin": True,
                    "content_day_local": current_budget_day,
                    "execution_limits": config.get("automation_reliability", {}).get("reserve", {}),
                    "idempotency_key": f"reserve:{current_budget_day}:pass:{pass_number}",
                }
            )

        for item in candidates:
            task_type = str(item.get("task_type", ""))
            action_lane = str(item.get("action_lane", ""))
            if action_lane == "direct-inbound":
                item["priority"] = 1
            elif action_lane == "soft-reciprocity":
                item["priority"] = 4
            else:
                item["priority"] = PRIORITY_BY_TYPE.get(
                    task_type, int(item.get("priority", 99))
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

        max_consecutive = int(
            config.get("automation_reliability", {}).get("max_consecutive_same_task_type", 2) or 2
        )
        if candidates:
            first_type = str(candidates[0].get("task_type", ""))
            consecutive = int(dispatcher.get("consecutive_same_task_type", 0) or 0)
            if (
                first_type not in STARVATION_EXEMPT_TYPES
                and dispatcher.get("last_selected_task_type") == first_type
                and consecutive >= max_consecutive
            ):
                alternative = next(
                    (
                        item
                        for item in candidates[1:]
                        if str(item.get("task_type", "")) != first_type
                    ),
                    None,
                )
                if alternative is not None:
                    candidates.remove(alternative)
                    candidates.insert(0, alternative)

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
        elif pending_count and reconcilable_count == 0 and future_wakes:
            wake = future_wakes[0]
            wake_at = iso_time(wake["at"])
            wake_trigger = str(wake["trigger"])
            result = {
                "valid": True,
                "decision": "wait",
                "decided_at": now,
                "unfinished_work_count": pending_count,
                "deferred_work_count": len(deferred_task_ids),
                "evidence": "all unfinished work is validly time-gated; no executable stage debt exists",
                "predicted_next_opportunity": wake_at,
                "wake_trigger": wake_trigger,
                "continuation": automatic_continuation(
                    state_dir,
                    config,
                    wake_at,
                    wake_trigger,
                ),
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
                continuation = automatic_continuation(
                    state_dir,
                    config,
                    str(next_wake_at),
                    str(next_wake_reason),
                )
                result = {
                    "valid": True,
                    "decision": "wait",
                    "decided_at": now,
                    "unfinished_work_count": 0,
                    "evidence": "validated work queue and stage ledger are empty",
                    "predicted_next_opportunity": next_wake_at,
                    "wake_trigger": next_wake_reason,
                    "continuation": continuation,
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
        result["budget_day_local"] = current_budget_day
        result["budget_day_reset"] = budget_day_reset
        result["reconciliation"] = reconciliation
        if args.record:
            if result.get("decision") == "execute" and isinstance(result.get("task"), dict):
                selected = result["task"]
                stored = next(
                    (
                        item
                        for item in items
                        if isinstance(item, dict) and item.get("task_id") == selected.get("task_id")
                    ),
                    None,
                )
                if stored is None:
                    stored = dict(selected)
                    items.append(stored)
                lease_minutes = int(
                    config.get("automation_reliability", {}).get("task_lease_minutes", 15) or 15
                )
                lease_task(
                    stored,
                    now_dt,
                    lease_minutes=lease_minutes,
                    lease_owner="adaptive-dispatcher",
                )
                result["task"] = dict(stored)
            queue["updated_at"] = now
            ledger["updated_at"] = now
            atomic_write(state_dir / "work-queue.json", queue)
            atomic_write(state_dir / "stage-ledger.json", ledger)
            record_decision(state_dir, state, result)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
