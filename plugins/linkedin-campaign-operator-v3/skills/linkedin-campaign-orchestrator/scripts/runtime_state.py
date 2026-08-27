#!/usr/bin/env python3
"""Shared deterministic state reconciliation for the campaign runtime."""

from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from opportunity_recovery import eligible_opportunities, opportunity_document


ACTIVE_TASK_STATUSES = {"pending", "recovering", "missed-recovering", "retry-wait"}
LEASED_TASK_STATUSES = {"leased", "running"}
TERMINAL_TASK_STATUSES = {"completed", "blocked", "superseded", "expired", "cancelled"}
RUNTIME_CLASSIFICATION_CONTRACT = "agent-neutral-runtime-v1"


def classify_lifecycle(
    state: dict[str, Any],
    *,
    consent_valid: bool | None = None,
) -> tuple[str, list[str]]:
    """Derive one lifecycle state from durable evidence for every compatible agent."""
    current = str(state.get("lifecycle_state") or "ready")
    if current in {"completed", "user-stopped"}:
        return current, [f"terminal-state:{current}"]
    if consent_valid is False:
        return "ready", ["consent-not-active"]

    dispatcher = state.get("dispatcher", {})
    if not isinstance(dispatcher, dict):
        dispatcher = {}
    linkedin_lane = str(dispatcher.get("linkedin_lane") or "ready")
    offline_lane = str(dispatcher.get("offline_lane") or "ready")
    if state.get("hard_blocker") and offline_lane == "blocked":
        return "hard-blocked", ["global-hard-blocker", "offline-lane-blocked"]

    recovering_reasons: list[str] = []
    if linkedin_lane != "ready":
        recovering_reasons.append(f"linkedin-lane:{linkedin_lane}")
    if offline_lane != "ready":
        recovering_reasons.append(f"offline-lane:{offline_lane}")
    circuits = dispatcher.get("lane_circuits", {})
    if isinstance(circuits, dict):
        for lane, circuit in sorted(circuits.items()):
            if not isinstance(circuit, dict):
                continue
            circuit_status = str(circuit.get("status") or "closed")
            if circuit_status != "closed":
                recovering_reasons.append(f"{lane}-circuit:{circuit_status}")
            if circuit.get("intervention_required") is True:
                recovering_reasons.append(f"{lane}-intervention-required")
    if recovering_reasons:
        return "recovering", recovering_reasons
    return "running", ["all-required-lanes-ready"]


def apply_lifecycle_classification(
    state: dict[str, Any],
    now: datetime,
    *,
    consent_valid: bool | None = None,
) -> dict[str, Any]:
    lifecycle, reasons = classify_lifecycle(state, consent_valid=consent_valid)
    state["lifecycle_state"] = lifecycle
    classification = {
        "contract": RUNTIME_CLASSIFICATION_CONTRACT,
        "agent_neutral": True,
        "source_of_truth": "durable-runtime-evidence",
        "state": lifecycle,
        "reasons": reasons,
        "evaluated_at": iso_time(now),
    }
    state["runtime_classification"] = classification
    return classification


def reconcile_recovered_lane_continuation(
    state: dict[str, Any],
    now: datetime,
) -> bool:
    """Clear an obsolete lane-probe wake after its dependency is healthy again."""
    dispatcher = state.get("dispatcher", {})
    if not isinstance(dispatcher, dict):
        return False
    continuation = dispatcher.get("continuation", {})
    if not isinstance(continuation, dict):
        return False
    trigger = str(continuation.get("wake_trigger") or "")
    prefix = "lane-recovery-probe:"
    if not trigger.startswith(prefix):
        return False
    lane = trigger[len(prefix):]
    circuits = dispatcher.get("lane_circuits", {})
    circuit = circuits.get(lane, {}) if isinstance(circuits, dict) else {}
    lane_ready = dispatcher.get(f"{lane}_lane") == "ready"
    circuit_closed = isinstance(circuit, dict) and circuit.get("status", "closed") == "closed"
    if not (lane_ready and circuit_closed):
        return False
    continuation.update(
        {
            "status": "active",
            "owner_input_required": False,
            "next_wake_at": None,
            "wake_trigger": None,
            "action": None,
            "last_woke_at": iso_time(now),
            "last_completion_reason": f"{lane}-lane-recovered",
        }
    )
    return True


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False) + "\n")


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def current_time(value: str | None = None) -> datetime:
    return parse_time(value) if value else datetime.now(timezone.utc)


def iso_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def campaign_timezone(config: dict[str, Any]) -> ZoneInfo:
    name = str(config.get("timezone") or "UTC")
    try:
        return ZoneInfo(name)
    except Exception as exc:
        raise ValueError(f"invalid campaign timezone: {name}") from exc


def campaign_day(value: datetime, config: dict[str, Any]) -> str:
    return value.astimezone(campaign_timezone(config)).date().isoformat()


def required_regions(config: dict[str, Any]) -> tuple[str, ...]:
    configured = config.get("publishing_optimization", {}).get("required_regions", [])
    if not isinstance(configured, list):
        configured = []
    regions = tuple(str(region) for region in configured if isinstance(region, str) and region)
    return regions or ("india", "us-central")


def consent_fingerprint(consent: dict[str, Any]) -> str:
    stable = {
        "campaign_id": consent.get("campaign_id"),
        "consent_version": consent.get("consent_version"),
        "owner": consent.get("owner"),
        "status": consent.get("status"),
        "scope": consent.get("scope"),
        "receipt_id": consent.get("authorization_receipt", {}).get("receipt_id"),
        "approved_action_classes": consent.get("approved_action_classes"),
        "persistent_settings": consent.get("persistent_settings"),
    }
    encoded = json.dumps(stable, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def sync_consent_snapshot(
    state_dir: Path,
    state: dict[str, Any],
    now: datetime,
) -> tuple[bool, str | None]:
    path = state_dir / "consent-record.json"
    if not path.is_file():
        return False, "consent-record-missing"
    consent = load_object(path)
    receipt = consent.get("authorization_receipt", {})
    owner = consent.get("owner", {})
    account_profiles = [
        account
        for account in consent.get("accounts", [])
        if isinstance(account, dict) and account.get("type") == "linkedin-profile"
    ]
    valid = bool(
        consent.get("status") == "active"
        and consent.get("scope") == "campaign-lifetime"
        and consent.get("campaign_id") == state.get("campaign_id")
        and isinstance(owner, dict)
        and owner.get("display_name")
        and account_profiles
        and account_profiles[0].get("url")
        and isinstance(receipt, dict)
        and receipt.get("receipt_id")
        and receipt.get("granted_at")
    )
    snapshot = state.setdefault("automation_consent", {})
    snapshot.update(
        {
            "record_path": "consent-record.json",
            "status": consent.get("status", "missing"),
            "scope": consent.get("scope"),
            "receipt_id": receipt.get("receipt_id") if isinstance(receipt, dict) else None,
            "fingerprint": consent_fingerprint(consent),
            "loaded_at": iso_time(now),
            "reconfirmation_required": not valid,
        }
    )
    if account_profiles and account_profiles[0].get("url"):
        binding = state.setdefault("dispatcher", {}).setdefault("browser_binding", {})
        binding["expected_profile_url"] = account_profiles[0]["url"]
        binding["expected_profile_name"] = owner.get("expected_linkedin_identity") or owner.get(
            "display_name"
        )
    return valid, None if valid else "one-time-owner-consent-required"


def find_daily_packages(
    state_dir: Path,
    day: str,
    regions: tuple[str, ...],
) -> dict[str, str]:
    packages: dict[str, str] = {}
    for path in sorted(state_dir.glob(f"**/publication-package*{day}*.json")):
        try:
            value = load_object(path)
        except (OSError, json.JSONDecodeError, ValueError):
            continue
        package_day = (
            value.get("content_day_local")
            or value.get("content_day_ist")
            or value.get("content_day")
        )
        region = value.get("target_region") or value.get("region")
        status = value.get("final_validation_status") or value.get("validation_status")
        if package_day != day or region not in regions:
            continue
        if not isinstance(status, str) or not status.startswith("ready"):
            continue
        packages[str(region)] = str(path.relative_to(state_dir))
    return packages


def read_publication_evidence(
    state_dir: Path,
    day: str,
    regions: tuple[str, ...],
) -> dict[str, dict[str, Any]]:
    path = state_dir / "publication-evidence.jsonl"
    evidence: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return evidence
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(value, dict) or (
            value.get("content_day_local") or value.get("content_day_ist")
        ) != day:
            continue
        region = value.get("region")
        if value.get("verified") is True:
            key = str(region) if region in regions else str(value.get("post_id") or value.get("task_id"))
            evidence[key] = value
    return evidence


def upsert_task(items: list[dict[str, Any]], task: dict[str, Any]) -> dict[str, Any]:
    task_id = task["task_id"]
    for item in items:
        if item.get("task_id") == task_id:
            if item.get("status") not in TERMINAL_TASK_STATUSES:
                for key, value in task.items():
                    item.setdefault(key, value)
            return item
    items.append(task)
    return task


def upsert_stage(stages: list[dict[str, Any]], stage: dict[str, Any]) -> dict[str, Any]:
    stage_id = stage["stage_id"]
    for current in stages:
        if current.get("stage_id") == stage_id:
            return current
    stages.append(stage)
    return stage


def reconcile_content_day(
    state_dir: Path,
    state: dict[str, Any],
    config: dict[str, Any],
    queue: dict[str, Any],
    ledger: dict[str, Any],
    now: datetime,
) -> dict[str, Any]:
    day = campaign_day(now, config)
    timezone_value = campaign_timezone(config)
    regions = required_regions(config)
    publishing = state.setdefault("publishing", {})
    previous_day = publishing.get("content_day_local") or publishing.get("content_day_ist")
    rollover = previous_day != day
    items = queue.setdefault("items", [])
    stages = ledger.setdefault("stages", [])
    if not isinstance(items, list) or not isinstance(stages, list):
        raise ValueError("work queue items and stage ledger stages must be arrays")

    if rollover and previous_day:
        history = publishing.setdefault("day_history", [])
        if not any(
            (entry.get("content_day_local") or entry.get("content_day_ist")) == previous_day
            for entry in history
            if isinstance(entry, dict)
        ):
            history.append(
                {
                    "content_day_local": previous_day,
                    "packages_ready": int(publishing.get("packages_ready", 0) or 0),
                    "posts_published": int(publishing.get("posts_published", 0) or 0),
                    "published_post_ids": list(publishing.get("published_post_ids", [])),
                    "last_publication_at": publishing.get("last_publication_at"),
                    "closed_at": iso_time(now),
                    "closure_reason": "automatic-local-day-rollover",
                }
            )
        for item in items:
            if not isinstance(item, dict):
                continue
            item_day = item.get("content_day_local") or item.get("content_day_ist")
            if (
                item.get("task_type") in {"publication-opportunity", "publication-queue-building"}
                and item_day
                and item_day != day
                and item.get("status") not in TERMINAL_TASK_STATUSES
            ):
                item["status"] = "superseded"
                item["completed_at"] = iso_time(now)
                item["completion_reason"] = "content-day-closed"
            if (
                item.get("task_type") in {"performance-recovery-content", "performance-recovery-analytics"}
                and item_day
                and item_day != day
                and item.get("status") not in TERMINAL_TASK_STATUSES
            ):
                item["status"] = "expired"
                item["completed_at"] = iso_time(now)
                item["completion_reason"] = "recovery-package-expired-at-content-day-rollover"

    packages = find_daily_packages(state_dir, day, regions)
    evidence = read_publication_evidence(state_dir, day, regions)
    analytics_due_at = (
        datetime.fromisoformat(f"{day}T23:50:00")
        .replace(tzinfo=timezone_value)
        .astimezone(timezone.utc)
    )
    if rollover:
        publishing.update(
            {
                "content_day_local": day,
                "content_day_ist": day,
                "packages_required": len(regions),
                "posts_published": len(evidence),
                "published_post_ids": [
                    item.get("post_id") or item.get("post_url")
                    for item in evidence.values()
                    if item.get("post_id") or item.get("post_url")
                ],
                "last_publication_at": max(
                    (item.get("published_at") for item in evidence.values() if item.get("published_at")),
                    default=None,
                ),
                "current_cannibalization_signal": None,
                "normal_posts_published": sum(1 for region in regions if region in evidence),
                "recovery_posts_published": sum(1 for key in evidence if key not in regions),
                "recovery_package": None,
            }
        )
    publishing["packages_ready"] = len(packages)
    publishing["packages_required"] = len(regions)
    publishing["content_day_local"] = day
    publishing["content_day_ist"] = day
    publishing["prepared_packages"] = [
        {"package": path, "region": region, "content_day_local": day}
        for region, path in sorted(packages.items())
    ]

    preflight_stage = upsert_stage(
        stages,
        {
            "stage_id": f"preflight-{day}",
            "stage_type": "preflight",
            "status": "pending",
            "required_artifacts": [],
            "completed_artifacts": [],
            "content_day_local": day,
        },
    )
    upsert_task(
        items,
        {
            "task_id": f"preflight-{day}",
            "task_type": "preflight",
            "lane": "offline",
            "priority": 1,
            "status": "completed" if preflight_stage.get("status") == "completed" else "pending",
            "ready": True,
            "requires_linkedin": False,
            "content_day_ist": day,
            "stage_id": f"preflight-{day}",
            "idempotency_key": f"preflight:{day}",
        },
    )

    production_id = f"prepare-two-packages-{day}"
    production = upsert_task(
        items,
        {
            "task_id": production_id,
            "task_type": "two-package-production",
            "lane": "offline",
            "priority": 5,
            "status": "completed" if len(packages) == len(regions) else "pending",
            "ready": True,
            "requires_linkedin": False,
            "content_day_local": day,
            "required_regions": list(regions),
            "required_package_count": len(regions),
            "no_third_package": True,
            "idempotency_key": f"packages:{day}",
        },
    )
    if len(packages) == len(regions) and production.get("status") not in TERMINAL_TASK_STATUSES:
        production["status"] = "completed"
        production["completed_at"] = iso_time(now)
        production["completion_reason"] = "daily-packages-verified"

    for item in items:
        if (
            isinstance(item, dict)
            and item.get("task_type") == "publication-opportunity"
            and item.get("task_id") == f"publish-{day}-pair"
            and item.get("status") not in TERMINAL_TASK_STATUSES
        ):
            item["status"] = "superseded"
            item["completed_at"] = iso_time(now)
            item["completion_reason"] = "replaced-by-region-specific-publication-tasks"

    for region, package_path in packages.items():
        publication = upsert_task(
            items,
            {
                "task_id": f"publish-{region}-{day}",
                "task_type": "publication-opportunity",
                "lane": "linkedin",
                "priority": 2,
                "status": "completed" if region in evidence else "pending",
                "ready": True,
                "requires_linkedin": True,
                "engagement_queue_ready": False,
                "content_day_local": day,
                "region": region,
                "package_path": package_path,
                "idempotency_key": f"publish:{day}:{region}",
            },
        )
        if region in evidence:
            publication["status"] = "completed"
            publication["completed_at"] = evidence[region].get("published_at") or iso_time(now)
            publication["external_evidence"] = evidence[region]

    package_stage = upsert_stage(
        stages,
        {
            "stage_id": f"packages-{day}",
            "stage_type": "content-production",
            "status": "completed" if len(packages) == len(regions) else "pending",
            "required_artifacts": list(packages.values()) if len(packages) == len(regions) else [],
            "completed_artifacts": list(packages.values()),
            "content_day_local": day,
        },
    )
    if len(packages) == len(regions):
        package_stage["status"] = "completed"
        package_stage["required_artifacts"] = list(packages.values())
        package_stage["completed_artifacts"] = list(packages.values())

    for region in regions:
        publication_stage = upsert_stage(
            stages,
            {
                "stage_id": f"publish-{region}-{day}",
                "stage_type": "publication",
                "status": "completed" if region in evidence else "pending",
                "required_artifacts": ["publication-evidence.jsonl"],
                "completed_artifacts": ["publication-evidence.jsonl"] if region in evidence else [],
                "content_day_local": day,
                "region": region,
                "evidence_recorded": region in evidence,
            },
        )
        if region in evidence:
            publication_stage["status"] = "completed"
            publication_stage["completed_at"] = (
                evidence[region].get("published_at") or iso_time(now)
            )
            publication_stage["completed_artifacts"] = ["publication-evidence.jsonl"]
            publication_stage["evidence_recorded"] = True
            publication_stage["completion_evidence"] = evidence[region]
    upsert_stage(
        stages,
        {
            "stage_id": f"analytics-{day}",
            "stage_type": "analytics",
            "status": "pending",
            "required_artifacts": ["daily-analytics.jsonl", "learning-ledger.jsonl"],
            "completed_artifacts": [],
            "content_day_local": day,
            "learning_recorded": False,
            "learning_status": None,
            "experiment_outcome": None,
            "next_measurement_trigger": None,
            "due_at": iso_time(analytics_due_at),
        },
    )
    return {
        "content_day_local": day,
        "content_day_ist": day,
        "previous_content_day_local": previous_day,
        "rollover_performed": rollover,
        "packages_ready": len(packages),
        "posts_published": len(evidence) if rollover else int(publishing.get("posts_published", 0) or 0),
    }


def reconcile_task_lifecycle(
    queue: dict[str, Any],
    now: datetime,
    *,
    startup: bool,
) -> dict[str, Any]:
    items = queue.setdefault("items", [])
    if not isinstance(items, list):
        raise ValueError("work-queue.json items must be an array")
    expired_leases: list[str] = []
    missed_tasks: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        status = item.get("status")
        lease_expires = parse_time(item.get("lease_expires_at"))
        if status in LEASED_TASK_STATUSES and (startup or (lease_expires and lease_expires <= now)):
            item["status"] = "recovering"
            item["ready"] = True
            item["recovery_reason"] = "abandoned-task-lease-after-restart" if startup else "task-lease-expired"
            item["recovered_at"] = iso_time(now)
            item["lease_id"] = None
            item["leased_at"] = None
            item["lease_expires_at"] = None
            expired_leases.append(str(item.get("task_id")))
        if status == "retry-wait":
            next_eligible = parse_time(item.get("next_eligible_at"))
            if next_eligible is None or next_eligible <= now:
                item["status"] = "recovering"
                item["ready"] = True
        due_at = parse_time(item.get("due_at"))
        if (
            startup
            and due_at
            and due_at < now
            and item.get("status") in ACTIVE_TASK_STATUSES
            and item.get("task_type") not in {"publication-opportunity", "publication-queue-building"}
        ):
            item["status"] = "missed-recovering"
            item["recovery_reason"] = "due-during-session-downtime"
            missed_tasks.append(str(item.get("task_id")))
    return {"expired_leases": expired_leases, "missed_tasks": missed_tasks}


def recalculate_adaptive_reserve(
    state: dict[str, Any],
    config: dict[str, Any],
    now: datetime,
    state_dir: Path | None = None,
) -> dict[str, Any]:
    scaling = state.setdefault("engagement_scaling", {})
    reserve = scaling.setdefault("adaptive_reserve", {})
    rules = config.get("automation_reliability", {}).get("reserve", {})
    burst_history = scaling.get("burst_history", [])
    recent_sizes = [
        int(item.get("actions_executed", 0) or 0)
        for item in burst_history[-6:]
        if isinstance(item, dict) and int(item.get("actions_executed", 0) or 0) > 0
    ]
    expected = (
        sum(recent_sizes) / len(recent_sizes)
        if recent_sizes
        else float(reserve.get("expected_burst_size") or rules.get("default_expected_burst_size", 5))
    )
    expected = min(10.0, max(1.0, expected))
    forecast = max(1, int(reserve.get("forecast_bursts", 2) or 2))
    staleness = min(1.0, max(0.0, float(reserve.get("staleness_rate", 0) or 0)))
    rejection = min(1.0, max(0.0, float(reserve.get("rejection_rate", 0) or 0)))
    minimum = max(1, int(rules.get("min_target", 4) or 4))
    maximum = min(20, max(minimum, int(rules.get("max_target", 20) or 20)))
    base_remaining = max(
        0,
        int(scaling.get("base_daily_ceiling", 100) or 100)
        - int(scaling.get("base_actions_used", 0) or 0),
    )
    # Rejection and staleness rotate discovery effort; they never inflate supply
    # demand or manufacture a larger reserve target.
    calculated = math.ceil(expected * forecast)
    target = 0 if base_remaining == 0 else min(maximum, base_remaining, max(minimum, calculated))
    canonical_count = int(reserve.get("qualified_count", 0) or 0)
    if state_dir is not None:
        canonical = opportunity_document(state_dir, str(state.get("campaign_id") or ""))
        canonical_count = len(eligible_opportunities(canonical, state, config, now))
    reserve.update(
        {
            "expected_burst_size": round(expected, 2),
            "forecast_bursts": forecast,
            "target_count": target,
            "target_calculated_at": iso_time(now),
            "target_inputs": {
                "staleness_rate": staleness,
                "rejection_rate": rejection,
                "base_remaining": base_remaining,
                "minimum": minimum,
                "maximum": maximum,
            },
            "qualified_count": canonical_count,
            "count_source": "engagement-opportunities.json",
        }
    )
    reserve["note"] = (
        f"Adaptive reserve is {int(reserve.get('qualified_count', 0) or 0)}/{target}; "
        f"target derives from expected burst size {round(expected, 2)} and remaining base capacity "
        f"{base_remaining}; staleness {staleness:.2f} and rejection {rejection:.2f} affect source rotation only."
    )
    return reserve


def reconcile_runtime(
    state_dir: Path,
    state: dict[str, Any],
    config: dict[str, Any],
    queue: dict[str, Any],
    ledger: dict[str, Any],
    now: datetime,
    *,
    startup: bool = False,
) -> dict[str, Any]:
    day = campaign_day(now, config)
    scaling = state.setdefault("engagement_scaling", {})
    budget_reset = scaling.get("budget_day_local") != day
    if budget_reset:
        scaling["budget_day_local"] = day
        scaling["base_actions_used"] = 0
        scaling["direct_reply_overage"] = 0
    consent_valid, consent_reason = sync_consent_snapshot(state_dir, state, now)
    lifecycle = reconcile_task_lifecycle(queue, now, startup=startup)
    publishing = reconcile_content_day(state_dir, state, config, queue, ledger, now)
    reserve = recalculate_adaptive_reserve(state, config, now, state_dir)
    continuation_reconciled = reconcile_recovered_lane_continuation(state, now)
    runtime_classification = apply_lifecycle_classification(
        state,
        now,
        consent_valid=consent_valid,
    )
    continuity = state.setdefault("runtime_continuity", {})
    previous_heartbeat = parse_time(continuity.get("last_heartbeat_at"))
    if startup:
        continuity["restart_count"] = int(continuity.get("restart_count", 0) or 0) + 1
        continuity["last_session_started_at"] = iso_time(now)
        continuity["detected_downtime_seconds"] = (
            max(0, int((now - previous_heartbeat).total_seconds())) if previous_heartbeat else None
        )
        continuity["recovery_status"] = "reconciled"
        continuity["last_recovery_report"] = {
            "reconciled_at": iso_time(now),
            "expired_leases": lifecycle["expired_leases"],
            "missed_tasks": lifecycle["missed_tasks"],
            "rollover_performed": publishing["rollover_performed"],
            "content_day_local": day,
        }
    continuity["last_heartbeat_at"] = iso_time(now)
    queue["updated_at"] = iso_time(now)
    ledger["updated_at"] = iso_time(now)
    state["updated_at"] = iso_time(now)
    return {
        "content_day": publishing,
        "task_lifecycle": lifecycle,
        "adaptive_reserve": reserve,
        "budget_day_reset": budget_reset,
        "consent_valid": consent_valid,
        "consent_reason": consent_reason,
        "continuation_reconciled": continuation_reconciled,
        "runtime_classification": runtime_classification,
    }


def lease_task(
    item: dict[str, Any],
    now: datetime,
    *,
    lease_minutes: int,
    lease_owner: str,
) -> dict[str, Any]:
    attempt = int(item.get("attempt_count", 0) or 0) + 1
    lease_id = hashlib.sha256(
        f"{item.get('task_id')}:{iso_time(now)}:{attempt}".encode("utf-8")
    ).hexdigest()[:20]
    item.update(
        {
            "status": "leased",
            "attempt_count": attempt,
            "lease_id": lease_id,
            "lease_owner": lease_owner,
            "leased_at": iso_time(now),
            "lease_expires_at": iso_time(now + timedelta(minutes=lease_minutes)),
            "last_heartbeat_at": iso_time(now),
        }
    )
    return item
