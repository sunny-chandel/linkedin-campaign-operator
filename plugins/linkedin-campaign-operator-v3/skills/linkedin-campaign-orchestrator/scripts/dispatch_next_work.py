#!/usr/bin/env python3
"""Choose the next campaign task or emit a justified adaptive wait decision."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
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
from opportunity_recovery import (
    eligible_opportunities,
    evaluate_health,
    next_discovery_source,
    opportunity_document,
)
from dispatch_contract import dispatch_contract
from service_readiness import normalize_action_class, readiness_report, task_readiness


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
    "publication-execution": 2,
    "publication-queue-building": 2,
    "mandatory-stage-recovery": 3,
    "engagement-burst": 3,
    "engagement-burst-execution": 3,
    "soft-reciprocity": 4,
    "engagement-opportunity-generation": 5,
    "opportunity-discovery": 5,
    "performance-recovery-content": 5,
    "two-package-production": 5,
    "six-package-replenishment": 5,
    "regional-allocation": 5,
    "rolling-output-evaluation": 2,
    "publishing-debt-recovery": 2,
    "runtime-repair": 1,
    "scheduled-analytics-snapshot": 4,
    "opportunity-health-evaluation": 7,
    "performance-recovery-analytics": 7,
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
    "publication-execution",
    "publication-queue-building",
    "mandatory-stage-recovery",
    "engagement-burst",
    "engagement-burst-execution",
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
        return False, "rolling-action-cap"
    if task_type in {"publication-opportunity", "publication-execution", "publication-queue-building"} and posts_published >= 8:
        return False, "rolling-publication-cap-reached"
    if task_type in {"two-package-production", "six-package-replenishment"} and packages_ready >= 6:
        return False, "six-package-inventory-ready"
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
        "setup_input_required": False,
        "action": "arm-or-update-single-host-wake",
        "dedupe_key": f"linkedin-campaign-continuation:{campaign_id}",
        "expiry_policy": "renew-before-host-limit-until-target-or-stop-signal",
        "renew_existing_automation": True,
        "campaign_completion_or_stop_signal_required_to_end": True,
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
    recovery: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    wakes: list[dict[str, Any]] = []
    circuits = dispatcher.get("lane_circuits", {})
    linkedin_probe_at = None
    if isinstance(circuits, dict):
        linkedin_circuit = circuits.get("linkedin", {})
        if isinstance(linkedin_circuit, dict):
            candidate_probe = parse_time(linkedin_circuit.get("next_probe_at"))
            if candidate_probe and candidate_probe > now_dt:
                linkedin_probe_at = candidate_probe
    for item in items:
        if not isinstance(item, dict):
            continue
        status = item.get("status")
        next_eligible = parse_time(item.get("next_eligible_at"))
        due_at = parse_time(item.get("due_at"))
        decision_evidence = item.get("decision_evidence", {})
        next_evaluation_at = (
            parse_time(decision_evidence.get("next_evaluation_at"))
            if isinstance(decision_evidence, dict)
            else None
        )
        requires_linkedin = item.get("requires_linkedin") is True or item.get("lane") == "linkedin"
        if (
            status in UNFINISHED_STATUSES
            and requires_linkedin
            and dispatcher.get("linkedin_lane", "ready") != "ready"
            and linkedin_probe_at is not None
        ):
            wakes.append(
                {
                    "at": linkedin_probe_at,
                    "trigger": f"lane-recovery-unblocks:{item.get('task_id')}",
                    "task_id": item.get("task_id"),
                }
            )
        elif status == "retry-wait" and next_eligible and next_eligible > now_dt:
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
        elif (
            status in UNFINISHED_STATUSES
            and item.get("ready") is False
            and next_evaluation_at
            and next_evaluation_at > now_dt
        ):
            wakes.append(
                {
                    "at": next_evaluation_at,
                    "trigger": f"publication-decision-reevaluation:{item.get('task_id')}",
                    "task_id": item.get("task_id"),
                }
            )
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
    source_performance = (recovery or {}).get("source_performance", {})
    if isinstance(source_performance, dict):
        for source, record in source_performance.items():
            if not isinstance(record, dict):
                continue
            backoff_until = parse_time(record.get("backoff_until"))
            if backoff_until and backoff_until > now_dt:
                wakes.append(
                    {
                        "at": backoff_until,
                        "trigger": f"discovery-source-backoff-expired:{source}",
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
        health_evaluation = evaluate_health(state_dir, state, config, now_dt)
        canonical = opportunity_document(state_dir, str(state.get("campaign_id") or ""))
        consent = load_object(state_dir / "consent-record.json")
        executor = load_object(state_dir / "external-executor.json")
        configured_required = config.get("autonomous_execution", {}).get(
            "required_action_classes", ["publication", "comment", "reply", "reaction"]
        )
        campaign_readiness = readiness_report(
            executor,
            {
                action_class
                for value in configured_required
                if (action_class := normalize_action_class(value))
            },
        )
        engagement_executor_ready = any(
            readiness_report(executor, {action_class})["unattended_ready"]
            for action_class in ("comment", "reply", "reaction")
        )
        if args.record:
            state.setdefault("autonomous_execution", {}).update(
                {
                    "readiness_path": "external-executor.json",
                    "unattended_ready": campaign_readiness["unattended_ready"],
                    "last_checked_at": now,
                    "missing_capabilities": campaign_readiness["missing_capabilities"],
                }
            )
        canonical_candidates = eligible_opportunities(canonical, state, config, now_dt)
        canonical_candidates = [
            candidate
            for candidate in canonical_candidates
            if task_readiness(
                {
                    "task_type": "engagement-burst-execution",
                    "actions": [candidate],
                },
                executor,
            )["unattended_ready"]
        ]
        reserve = state.setdefault("engagement_scaling", {}).setdefault("adaptive_reserve", {})
        reserve["qualified_count"] = len(canonical_candidates)
        reserve["count_source"] = "engagement-opportunities.json"
        if args.record:
            append_jsonl(state_dir / "opportunity-health.jsonl", health_evaluation)
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
            existing_repair = next(
                (
                    item for item in blocker_items
                    if isinstance(item, dict)
                    and item.get("task_type") == "runtime-repair"
                    and item.get("status") in UNFINISHED_STATUSES
                ),
                None,
            )
            repair_task = existing_repair or {
                "task_id": f"runtime-repair-{now_dt.strftime('%Y%m%dT%H%M%SZ')}",
                "task_type": "runtime-repair",
                "lane": "offline",
                "priority": 1,
                "status": "pending",
                "ready": True,
                "requires_linkedin": False,
                "failure_evidence": state["hard_blocker"],
                "checkpoint": state.get("last_confirmed_action"),
                "idempotency_key": f"runtime-repair:{state.get('campaign_id')}",
            }
            repair_task["dispatch_contract"] = dispatch_contract(
                repair_task, consent, state, executor
            )
            if args.record and existing_repair is None:
                blocker_items.append(repair_task)
            if args.record and repair_task.get("status") in ACTIVE_STATUSES:
                lease_task(
                    repair_task,
                    now_dt,
                    lease_minutes=int(config.get("automation_reliability", {}).get("task_lease_minutes", 15) or 15),
                    lease_owner="adaptive-dispatcher",
                )
            result = {
                "valid": True,
                "decision": "execute",
                "decided_at": now,
                "priority": 1,
                "task": repair_task,
                "unfinished_work_count": blocker_unfinished,
                "reason": "automatic runtime repair precedes terminal blocker classification",
            }
            if args.record:
                atomic_write(state_dir / "work-queue.json", queue)
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
                "prompt": "Start the configured LinkedIn campaign? Pre-flight will verify the account and executor, store the operating receipt, and resume unfinished work from durable checkpoints.",
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
        base_used = int(scaling.get("rolling_24h_actions", scaling.get("base_actions_used", 0)) or 0)
        base_ceiling = int(scaling.get("rolling_action_cap", scaling.get("base_daily_ceiling", 200)) or 200)
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
        future_wakes = future_wake_candidates(
            items,
            dispatcher,
            now_dt,
            state.get("opportunity_recovery", {}),
        )
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
                and item.get("task_type") in {"publication-opportunity", "publication-execution"}
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

        repair_state = load_object(state_dir / "repair-state.json")
        if (
            dispatcher.get("linkedin_lane") != "ready"
            or repair_state.get("status") in {"repair-pending", "verification-pending", "recovering"}
        ) and not any(item.get("task_type") == "runtime-repair" for item in candidates):
            candidates.append({
                "task_id": "runtime-repair-active-capability",
                "task_type": "runtime-repair",
                "lane": "offline",
                "priority": 1,
                "status": "pending",
                "ready": True,
                "requires_linkedin": False,
                "active_repair": repair_state.get("active_repair"),
                "idempotency_key": f"runtime-repair:{state.get('campaign_id')}",
            })

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

        # The canonical opportunity file is authoritative. Legacy reserve tasks can never
        # claim supply or outrank an executable candidate.
        for item in items:
            if (
                isinstance(item, dict)
                and item.get("task_type") == "adaptive-reserve"
                and item.get("status") in UNFINISHED_STATUSES
            ):
                item["status"] = "superseded"
                item["completed_at"] = now
                item["completion_reason"] = "replaced-by-canonical-opportunity-generation"
        candidates = [item for item in candidates if item.get("task_type") != "adaptive-reserve"]

        if canonical_candidates:
            remaining = max(0, base_ceiling - base_used)
            burst_candidates = [
                item
                for item in canonical_candidates
                if item.get("lane") == "direct-inbound" or remaining > 0
            ][: min(10, max(1, remaining) if remaining else 10)]
            if burst_candidates and not any(
                isinstance(item, dict)
                and item.get("task_type") in {"engagement-burst", "engagement-burst-execution"}
                and item.get("status") in UNFINISHED_STATUSES
                for item in items
            ):
                candidate_ids = [str(item.get("candidate_id")) for item in burst_candidates]
                candidates.append(
                    {
                        "task_id": f"engagement-burst-{current_budget_day}-{'-'.join(candidate_ids)[:80]}",
                        "task_type": "engagement-burst-execution",
                        "lane": "linkedin",
                        "action_lane": (
                            "direct-inbound"
                            if all(item.get("lane") == "direct-inbound" for item in burst_candidates)
                            else "proactive"
                        ),
                        "priority": 1 if all(item.get("lane") == "direct-inbound" for item in burst_candidates) else 3,
                        "status": "pending",
                        "ready": True,
                        "requires_linkedin": True,
                        "content_day_local": current_budget_day,
                        "candidate_ids": candidate_ids,
                        "actions": burst_candidates,
                        "action_count": len(burst_candidates),
                        "active_recovery_mode": health_evaluation["mode"],
                        "idempotency_key": f"burst:{current_budget_day}:{':'.join(candidate_ids)}",
                    }
                )

        recovery = state.get("opportunity_recovery", {})
        reserve_target = max(40, int(scaling.get("adaptive_reserve", {}).get("target_count", 40) or 40))
        supply_weak = len(canonical_candidates) < reserve_target
        action_deficit = base_used < min(base_ceiling, int(health_evaluation["expected_actions"]))
        discovery_types = {"engagement-opportunity-generation", "opportunity-discovery"}
        active_discovery_exists = any(
            isinstance(item, dict)
            and item.get("task_type") in discovery_types
            and item.get("status") in ACTIVE_STATUSES | {"leased", "running"}
            for item in items
        )
        blocked_discovery_sources = {
            str(item.get("discovery_source"))
            for item in items
            if isinstance(item, dict)
            and item.get("task_type") in discovery_types
            and item.get("status") == "retry-wait"
            and parse_time(item.get("next_eligible_at")) is not None
            and parse_time(item.get("next_eligible_at")) > now_dt
            and item.get("discovery_source")
        }
        unknown_retry_wait_exists = any(
            isinstance(item, dict)
            and item.get("task_type") in discovery_types
            and item.get("status") == "retry-wait"
            and parse_time(item.get("next_eligible_at")) is not None
            and parse_time(item.get("next_eligible_at")) > now_dt
            and not item.get("discovery_source")
            for item in items
        )
        if (
            supply_weak
            and engagement_executor_ready
            and base_used < base_ceiling
            and (recovery.get("active") is True or action_deficit or base_used < 160)
            and dispatcher.get("linkedin_lane", "ready") == "ready"
            and not active_discovery_exists
            and not unknown_retry_wait_exists
            and not any(item.get("task_type") in discovery_types for item in candidates)
        ):
            source = next_discovery_source(
                state,
                config,
                now_dt,
                excluded_sources=blocked_discovery_sources,
            )
            attempts = sum(
                1
                for item in items
                if isinstance(item, dict)
                and item.get("task_type") in {"engagement-opportunity-generation", "opportunity-discovery"}
                and item.get("content_day_local") == current_budget_day
            ) + 1
            if source is not None:
                candidates.append(
                {
                    "task_id": f"generate-opportunities-{current_budget_day}-{attempts}-{source}",
                    "task_type": "opportunity-discovery",
                    "lane": "linkedin",
                    "priority": 5,
                    "status": "pending",
                    "ready": True,
                    "requires_linkedin": True,
                    "content_day_local": current_budget_day,
                    "discovery_source": source,
                    "active_recovery_mode": health_evaluation["mode"],
                    "canonical_output": "engagement-opportunities.json",
                    "idempotency_key": f"opportunity-generation:{current_budget_day}:{attempts}:{source}",
                }
                )

        minimum_posts = int(config.get("publishing_optimization", {}).get("minimum_posts_rolling_24h", 6) or 6)
        maximum_posts = int(config.get("publishing_optimization", {}).get("maximum_posts_rolling_24h", 8) or 8)
        posts_published = int(publishing.get("rolling_24h_posts", publishing.get("posts_published", 0)) or 0)
        last_publication = parse_time(publishing.get("last_publication_at"))
        spacing_ok = last_publication is None or now_dt - last_publication >= timedelta(minutes=120)
        velocity = publishing.get("preceding_post_velocity_ratio")
        cannibalization = publishing.get("current_cannibalization_signal")
        distribution_ok = (
            isinstance(velocity, (int, float)) and not isinstance(velocity, bool) and velocity < 0.85
        ) or (
            isinstance(cannibalization, (int, float)) and not isinstance(cannibalization, bool) and cannibalization < 0.35
        )
        recovery_package = publishing.get("recovery_package")
        if (
            recovery.get("active") is True
            and posts_published >= minimum_posts
            and posts_published < maximum_posts
            and spacing_ok
            and distribution_ok
        ):
            if not isinstance(recovery_package, dict) or recovery_package.get("status") not in {"ready", "published"}:
                if not any(item.get("task_type") in {"performance-recovery-content", "six-package-replenishment"} for item in candidates):
                    candidates.append(
                        {
                            "task_id": f"prepare-recovery-post-{current_budget_day}-{posts_published + 1}",
                            "task_type": "six-package-replenishment",
                            "lane": "offline",
                            "priority": 5,
                            "status": "pending",
                            "ready": True,
                            "requires_linkedin": False,
                            "content_day_local": current_budget_day,
                            "publication_number": posts_published + 1,
                            "maximum_unpublished_packages": 1,
                            "quality_rules_relaxed": False,
                            "requires_fresh_source_and_distinct_angle_format_pillar": True,
                            "idempotency_key": f"recovery-content:{current_budget_day}:{posts_published + 1}",
                        }
                    )
            elif recovery_package.get("status") == "ready" and float(recovery_package.get("publication_score", 0) or 0) >= 65:
                candidates.append(
                    {
                        "task_id": f"publish-recovery-{current_budget_day}-{posts_published + 1}",
                        "task_type": "publication-execution",
                        "publication_kind": "recovery",
                        "lane": "linkedin",
                        "priority": 2,
                        "status": "pending",
                        "ready": True,
                        "requires_linkedin": True,
                        "engagement_queue_ready": True,
                        "content_day_local": current_budget_day,
                        "region": recovery_package.get("region", "adaptive-recovery"),
                        "package_path": recovery_package.get("package_path"),
                        "opportunity_score": recovery_package.get("publication_score"),
                        "idempotency_key": f"publish-recovery:{current_budget_day}:{posts_published + 1}",
                    }
                )

        blocked_external: list[dict[str, Any]] = []
        executable_candidates: list[dict[str, Any]] = []
        for item in candidates:
            readiness = task_readiness(item, executor)
            if readiness["unattended_ready"]:
                executable_candidates.append(item)
            else:
                blocked_external.append(
                    {
                        "task_id": item.get("task_id"),
                        "task_type": item.get("task_type"),
                        "executor_state": readiness["executor_state"],
                        "required_action_classes": readiness["required_action_classes"],
                        "missing_capabilities": readiness["missing_capabilities"],
                    }
                )
        candidates = executable_candidates

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
            if task_type == "direct-inbound" or action_lane == "direct-inbound":
                selected["budget_class"] = "direct-inbound-outside-cap"
                if not overage_allowed:
                    raise ValueError("direct inbound outside-cap handling is disabled")
            elif task_type in BASE_BUDGET_TYPES or action_lane in BASE_BUDGET_TYPES:
                selected["budget_class"] = "base"
                selected["concentration_penalty"] = concentration_penalty
                selected["effective_opportunity_score"] = round(
                    float(selected.get("opportunity_score", 0) or 0)
                    - concentration_penalty * 100,
                    2,
                )
            selected["dispatch_contract"] = dispatch_contract(
                selected, consent, state, executor
            )
            result = {
                "valid": True,
                "decision": "execute",
                "decided_at": now,
                "task": selected,
                "unfinished_work_count": max(1, pending_count),
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
        elif blocked_external:
            result = {
                "valid": True,
                "decision": "blocked",
                "decided_at": now,
                "unfinished_work_count": pending_count,
                "blocked_external": blocked_external,
                "reason": "external work is parked until unattended executor readiness passes",
                "setup_input_required": False,
                "setup_event": "executor-readiness",
            }
        elif pending_count:
            offline_available = dispatcher.get("offline_lane", "ready") != "blocked"
            if offline_available:
                recovery_task_id = f"opportunity-health-recovery-{current_budget_day}"
                completed_recovery = next(
                    (
                        item
                        for item in items
                        if isinstance(item, dict)
                        and item.get("task_id") == recovery_task_id
                        and (item.get("status") == "completed" or item.get("completed_at"))
                    ),
                    None,
                )
                if completed_recovery is not None:
                    completed_recovery["status"] = "completed"
                    completed_recovery["next_eligible_at"] = None
                    for lease_key in (
                        "lease_id",
                        "lease_owner",
                        "leased_at",
                        "lease_expires_at",
                        "last_heartbeat_at",
                    ):
                        completed_recovery.pop(lease_key, None)
                    if future_wakes:
                        wake_at = iso_time(future_wakes[0]["at"])
                        wake_trigger = str(future_wakes[0]["trigger"])
                        evidence = (
                            "the daily health refresh is complete and the remaining work is "
                            "time-gated; reuse the earliest durable wake"
                        )
                    else:
                        continuation_config = config.get("adaptive_dispatch", {}).get(
                            "continuation", {}
                        )
                        if not isinstance(continuation_config, dict):
                            continuation_config = {}
                        fallback_minutes = int(
                            continuation_config.get("fallback_heartbeat_minutes", 15) or 15
                        )
                        fallback_minutes = max(1, fallback_minutes)
                        wake_at = iso_time(now_dt + timedelta(minutes=fallback_minutes))
                        wake_trigger = "fallback-heartbeat-after-health-refresh"
                        evidence = (
                            "the daily health refresh is complete and no task became executable; "
                            "resume on the configured automatic heartbeat"
                        )
                    result = {
                        "valid": True,
                        "decision": "wait",
                        "decided_at": now,
                        "unfinished_work_count": pending_count,
                        "deferred_work_count": len(deferred_task_ids),
                        "evidence": evidence,
                        "predicted_next_opportunity": wake_at,
                        "wake_trigger": wake_trigger,
                        "continuation": automatic_continuation(
                            state_dir,
                            config,
                            wake_at,
                            wake_trigger,
                        ),
                    }
                else:
                    recovery_task = {
                        "task_id": recovery_task_id,
                        "task_type": "opportunity-health-evaluation",
                        "lane": "offline",
                        "priority": 7,
                        "requires_linkedin": False,
                    }
                    recovery_task["dispatch_contract"] = dispatch_contract(
                        recovery_task, consent, state, executor
                    )
                    result = {
                        "valid": True,
                        "decision": "execute",
                        "decided_at": now,
                        "task": recovery_task,
                        "unfinished_work_count": pending_count,
                        "rejected": rejected,
                        "reason": "unfinished work is ineligible; refresh health and exact task evidence without a reconciliation loop",
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
                investigation_task = {
                    "task_id": "investigate-next-opportunity",
                    "task_type": "analytics-and-investigation",
                    "lane": "offline",
                    "priority": 8,
                    "requires_linkedin": False,
                }
                investigation_task["dispatch_contract"] = dispatch_contract(
                    investigation_task, consent, state, executor
                )
                result = {
                    "valid": True,
                    "decision": "execute",
                    "decided_at": now,
                    "task": investigation_task,
                    "unfinished_work_count": 0,
                    "reason": "waiting is invalid until an evidence-backed wake trigger exists",
                }
        result["budget_day_local"] = current_budget_day
        result["budget_day_reset"] = budget_day_reset
        result["reconciliation"] = reconciliation
        result["opportunity_health"] = health_evaluation
        result["canonical_eligible_candidates"] = len(canonical_candidates)
        result["executor_readiness"] = campaign_readiness
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
                else:
                    stored["dispatch_contract"] = selected.get(
                        "dispatch_contract"
                    )
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
