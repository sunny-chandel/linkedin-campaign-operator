#!/usr/bin/env python3
"""Persist consent, browser, pre-flight, task, lane, and reserve runtime events."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import timedelta
from pathlib import Path
from typing import Any

from runtime_state import (
    ACTIVE_TASK_STATUSES,
    apply_lifecycle_classification,
    append_jsonl,
    atomic_write,
    current_time,
    iso_time,
    load_object,
    parse_time,
    recalculate_adaptive_reserve,
    required_regions,
    sync_consent_snapshot,
)


PREFLIGHT_COMPONENTS = {
    "browser",
    "linkedin-identity",
    "claude-design",
    "file-upload",
    "brand",
    "premium",
    "account-baseline",
}


def write_runtime(
    state_dir: Path,
    state: dict[str, Any],
    queue: dict[str, Any] | None = None,
    ledger: dict[str, Any] | None = None,
) -> None:
    atomic_write(state_dir / "campaign-state.json", state)
    if queue is not None:
        atomic_write(state_dir / "work-queue.json", queue)
    if ledger is not None:
        atomic_write(state_dir / "stage-ledger.json", ledger)


def require_active_consent(state_dir: Path, state: dict[str, Any], now) -> None:
    valid, reason = sync_consent_snapshot(state_dir, state, now)
    if not valid:
        raise ValueError(reason or "one-time-owner-consent-required")


def find_task(queue: dict[str, Any], task_id: str) -> dict[str, Any]:
    items = queue.get("items", [])
    if not isinstance(items, list):
        raise ValueError("work-queue.json items must be an array")
    for item in items:
        if isinstance(item, dict) and item.get("task_id") == task_id:
            return item
    raise ValueError(f"unknown task_id: {task_id}")


def parse_payload(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    decoded = json.loads(value)
    if not isinstance(decoded, dict):
        raise ValueError("payload must decode to a JSON object")
    return decoded


def recognized_identity(consent: dict[str, Any]) -> tuple[str, str]:
    owner = consent.get("owner", {})
    owner_name = owner.get("display_name") if isinstance(owner, dict) else None
    profiles = [
        account
        for account in consent.get("accounts", [])
        if isinstance(account, dict) and account.get("type") == "linkedin-profile"
    ]
    profile_url = profiles[0].get("url") if profiles else None
    if not owner_name or not profile_url:
        raise ValueError("consent record requires a recognized owner and LinkedIn profile URL")
    return str(owner_name), str(profile_url)


def consent_grant(args, state_dir: Path, state: dict[str, Any], now) -> dict[str, Any]:
    consent_path = state_dir / "consent-record.json"
    consent = load_object(consent_path)
    existing = consent.get("authorization_receipt", {})
    if consent.get("status") == "active" and isinstance(existing, dict) and existing.get("receipt_id"):
        sync_consent_snapshot(state_dir, state, now)
        write_runtime(state_dir, state)
        return {
            "valid": True,
            "already_active": True,
            "receipt_id": existing["receipt_id"],
            "scope": consent.get("scope"),
            "reconfirmation_required": False,
        }
    expected_owner, _ = recognized_identity(consent)
    granted_by = args.owner or expected_owner
    if granted_by != expected_owner:
        raise ValueError("consent grant owner does not match the configured recognized owner")
    receipt_id = f"consent-{state.get('campaign_id')}-{int(now.timestamp())}"
    consent.update(
        {
            "schema_version": "2.0",
            "consent_version": "2.0",
            "status": "active",
            "scope": "campaign-lifetime",
            "activated_at": iso_time(now),
            "authorization_receipt": {
                "receipt_id": receipt_id,
                "granted_at": iso_time(now),
                "granted_by": granted_by,
                "source": args.source,
                "automation_mode": "fully-automated",
                "portable_across_model_sessions": True,
            },
            "reconfirmation_policy": {
                "routine_reconfirmation_required": False,
                "reload_on_every_session_start": True,
                "reask_only_when": [
                    "owner-revoked",
                    "consent-record-missing-or-invalid",
                    "verified-account-identity-changed",
                ],
            },
        }
    )
    settings = consent.setdefault("persistent_settings", [])
    for setting in (
        "one-time-high-value-consent",
        "campaign-lifetime-consent-reload",
        "automatic-recovery-without-routine-questions",
    ):
        if setting not in settings:
            settings.append(setting)
    atomic_write(consent_path, consent)
    sync_consent_snapshot(state_dir, state, now)
    state["lifecycle_state"] = "ready"
    state["updated_at"] = iso_time(now)
    write_runtime(state_dir, state)
    return {
        "valid": True,
        "already_active": False,
        "receipt_id": receipt_id,
        "scope": "campaign-lifetime",
        "reconfirmation_required": False,
    }


def consent_revoke(state_dir: Path, state: dict[str, Any], now) -> dict[str, Any]:
    consent_path = state_dir / "consent-record.json"
    consent = load_object(consent_path)
    consent["status"] = "revoked"
    consent["revoked_at"] = iso_time(now)
    atomic_write(consent_path, consent)
    sync_consent_snapshot(state_dir, state, now)
    state["lifecycle_state"] = "user-stopped"
    state["updated_at"] = iso_time(now)
    write_runtime(state_dir, state)
    return {"valid": True, "status": "revoked"}


def browser_bind(args, state_dir: Path, state: dict[str, Any], now) -> dict[str, Any]:
    require_active_consent(state_dir, state, now)
    consent = load_object(state_dir / "consent-record.json")
    _, expected_profile = recognized_identity(consent)
    dispatcher = state.setdefault("dispatcher", {})
    binding = dispatcher.setdefault("browser_binding", {})
    existing_id = binding.get("device_id")
    if existing_id and existing_id != args.device_id and not args.replace:
        raise ValueError(
            "approved browser is already pinned; use --replace only after an explicit owner reset"
        )
    binding.update(
        {
            "device_id": args.device_id,
            "device_label": args.device_label,
            "platform": args.platform,
            "expected_profile_url": expected_profile,
            "identity_verified": args.identity_verified,
            "bound_at": binding.get("bound_at") or iso_time(now),
            "last_seen_at": iso_time(now),
            "status": "ready" if args.identity_verified else "unverified",
            "selection_policy": "reuse-pinned-device-without-question",
        }
    )
    state["updated_at"] = iso_time(now)
    write_runtime(state_dir, state)
    return {"valid": True, "browser_binding": binding}


def preflight_record(args, state_dir: Path, state: dict[str, Any], now) -> dict[str, Any]:
    require_active_consent(state_dir, state, now)
    if args.component not in PREFLIGHT_COMPONENTS:
        raise ValueError(f"unsupported pre-flight component: {args.component}")
    config = load_object(state_dir / "campaign-config.json")
    default_ttl = int(
        config.get("automation_reliability", {}).get("preflight_evidence_ttl_minutes", 30) or 30
    )
    ttl = args.ttl_minutes if args.ttl_minutes is not None else default_ttl
    evidence = state.setdefault("preflight_evidence", {})
    binding = state.setdefault("dispatcher", {}).setdefault("browser_binding", {})
    evidence[args.component] = {
        "status": args.status,
        "checked_at": iso_time(now),
        "expires_at": iso_time(now + timedelta(minutes=max(1, ttl))),
        "evidence": args.evidence,
        "fingerprint": args.fingerprint,
        "browser_device_id": (
            binding.get("device_id")
            if args.component in {"browser", "linkedin-identity"}
            else None
        ),
    }
    evidence["last_updated_at"] = iso_time(now)
    if args.component == "browser" and args.status == "passed":
        binding["last_seen_at"] = iso_time(now)
        binding["status"] = "ready"
    state["updated_at"] = iso_time(now)
    write_runtime(state_dir, state)
    return {"valid": True, "component": args.component, "record": evidence[args.component]}


def preflight_status(state_dir: Path, state: dict[str, Any], now) -> dict[str, Any]:
    require_active_consent(state_dir, state, now)
    evidence = state.get("preflight_evidence", {})
    binding = state.get("dispatcher", {}).get("browser_binding", {})
    records: dict[str, Any] = {}
    reusable: list[str] = []
    expired: list[str] = []
    missing: list[str] = []
    for component in sorted(PREFLIGHT_COMPONENTS):
        record = evidence.get(component) if isinstance(evidence, dict) else None
        if not isinstance(record, dict):
            missing.append(component)
            continue
        expires_at = parse_time(record.get("expires_at"))
        device_matches = (
            component not in {"browser", "linkedin-identity"}
            or (
                bool(binding.get("device_id"))
                and record.get("browser_device_id") == binding.get("device_id")
            )
        )
        is_reusable = (
            record.get("status") == "passed"
            and expires_at is not None
            and expires_at > now
            and device_matches
        )
        records[component] = {**record, "reusable": is_reusable}
        (reusable if is_reusable else expired).append(component)
    return {
        "valid": True,
        "reusable_components": reusable,
        "expired_components": expired,
        "missing_components": missing,
        "browser_binding": binding,
        "records": records,
    }


def lane_event(args, state_dir: Path, state: dict[str, Any], now) -> dict[str, Any]:
    require_active_consent(state_dir, state, now)
    config = load_object(state_dir / "campaign-config.json")
    reliability = config.get("automation_reliability", {})
    circuit_config = reliability.get("circuit_breaker", {})
    max_retries = int(circuit_config.get("max_safe_retries", 2) or 2)
    cooldown = int(circuit_config.get("cooldown_minutes", 15) or 15)
    dispatcher = state.setdefault("dispatcher", {})
    circuits = dispatcher.setdefault("lane_circuits", {})
    circuit = circuits.setdefault(args.lane, {"status": "closed", "consecutive_failures": 0})
    if args.event == "recovered":
        circuit.update(
            {
                "status": "closed",
                "consecutive_failures": 0,
                "next_probe_at": None,
                "last_recovered_at": iso_time(now),
                "last_reason": args.reason,
                "intervention_required": False,
            }
        )
        dispatcher[f"{args.lane}_lane"] = "ready"
    elif args.event == "hard-blocker":
        circuit.update(
            {
                "status": "open",
                "consecutive_failures": max_retries,
                "next_probe_at": None,
                "last_failed_at": iso_time(now),
                "last_reason": args.reason,
                "intervention_required": True,
            }
        )
        dispatcher[f"{args.lane}_lane"] = "blocked"
    else:
        failures = int(circuit.get("consecutive_failures", 0) or 0) + 1
        opened = failures >= max_retries
        circuit.update(
            {
                "status": "open" if opened else "half-open",
                "consecutive_failures": failures,
                "next_probe_at": iso_time(now + timedelta(minutes=cooldown if opened else 1)),
                "last_failed_at": iso_time(now),
                "last_reason": args.reason,
                "intervention_required": False,
            }
        )
        dispatcher[f"{args.lane}_lane"] = "recovering"
    classification = apply_lifecycle_classification(state, now, consent_valid=True)
    state["updated_at"] = iso_time(now)
    write_runtime(state_dir, state)
    return {
        "valid": True,
        "lane": args.lane,
        "circuit": circuit,
        "runtime_classification": classification,
    }


def continuation_event(args, state_dir: Path, state: dict[str, Any], now) -> dict[str, Any]:
    require_active_consent(state_dir, state, now)
    dispatcher = state.setdefault("dispatcher", {})
    continuation = dispatcher.setdefault("continuation", {})
    timestamp = iso_time(now)
    if args.event == "armed":
        continuation.update(
            {
                "mode": "automatic",
                "status": "armed",
                "owner_input_required": False,
                "active_adapter": args.adapter,
                "automation_id": args.automation_id,
                "next_wake_at": args.next_wake_at or dispatcher.get("next_wake_at"),
                "armed_at": timestamp,
                "last_error": None,
            }
        )
    elif args.event == "woke":
        continuation.update(
            {
                "mode": "automatic",
                "status": "active",
                "owner_input_required": False,
                "active_adapter": args.adapter or continuation.get("active_adapter"),
                "automation_id": args.automation_id or continuation.get("automation_id"),
                "last_woke_at": timestamp,
                "last_error": None,
            }
        )
    else:
        failed_adapters = continuation.setdefault("failed_adapters", [])
        if args.adapter and args.adapter not in failed_adapters:
            failed_adapters.append(args.adapter)
        continuation.update(
            {
                "mode": "automatic",
                "status": "fallback-required",
                "owner_input_required": False,
                "last_failed_at": timestamp,
                "last_error": args.reason,
            }
        )
    state["updated_at"] = timestamp
    write_runtime(state_dir, state)
    return {"valid": True, "continuation": continuation}


def task_event(args, state_dir: Path, state: dict[str, Any], now) -> dict[str, Any]:
    require_active_consent(state_dir, state, now)
    queue = load_object(state_dir / "work-queue.json")
    ledger = load_object(state_dir / "stage-ledger.json")
    item = find_task(queue, args.task_id)
    payload = parse_payload(args.payload)
    timestamp = iso_time(now)
    continuity = state.setdefault("runtime_continuity", {})
    continuity["last_heartbeat_at"] = timestamp
    if args.event == "start":
        if item.get("status") not in {"leased", "recovering", "pending", "missed-recovering"}:
            raise ValueError(f"task cannot start from status {item.get('status')}")
        item["status"] = "running"
        item["started_at"] = item.get("started_at") or timestamp
        item["last_heartbeat_at"] = timestamp
        state["current_stage"] = item.get("task_type")
    elif args.event == "checkpoint":
        if item.get("status") not in {"leased", "running", "recovering"}:
            raise ValueError(f"task cannot checkpoint from status {item.get('status')}")
        item["status"] = "running"
        item["last_heartbeat_at"] = timestamp
        item["checkpoint"] = payload
        item["checkpointed_at"] = timestamp
        state["current_stage"] = item.get("task_type")
        state["last_confirmed_action"] = f"checkpoint:{args.task_id}"
    elif args.event == "complete":
        if item.get("status") == "completed":
            return {"valid": True, "idempotent": True, "task": item}
        if item.get("task_type") == "publication-opportunity":
            required = {"region", "post_id", "post_url"}
            missing = [key for key in required if not payload.get(key)]
            if missing or payload.get("verified") is not True:
                raise ValueError(
                    "publication completion requires verified region, post_id, and post_url evidence"
                )
            publishing = state.setdefault("publishing", {})
            day = (
                item.get("content_day_local")
                or item.get("content_day_ist")
                or publishing.get("content_day_local")
                or publishing.get("content_day_ist")
            )
            evidence = {
                "schema_version": "1.0",
                "campaign_id": state.get("campaign_id"),
                "content_day_local": day,
                "region": payload["region"],
                "post_id": payload["post_id"],
                "post_url": payload["post_url"],
                "published_at": payload.get("published_at") or timestamp,
                "verified": True,
                "task_id": item.get("task_id"),
                "package_path": item.get("package_path"),
            }
            append_jsonl(state_dir / "publication-evidence.jsonl", evidence)
            ids = publishing.setdefault("published_post_ids", [])
            if payload["post_id"] not in ids:
                ids.append(payload["post_id"])
            config = load_object(state_dir / "campaign-config.json")
            publishing["posts_published"] = min(len(required_regions(config)), len(ids))
            publishing["last_publication_at"] = evidence["published_at"]
        if item.get("task_type") == "preflight" and payload.get("preflight_passed") is not True:
            raise ValueError("preflight completion requires preflight_passed=true")
        if item.get("task_type") == "publication-queue-building":
            source_id = item.get("source_publication_task_id")
            if source_id:
                find_task(queue, str(source_id))["engagement_queue_ready"] = True
        item.update(
            {
                "status": "completed",
                "completed_at": timestamp,
                "completion_evidence": payload,
                "lease_id": None,
                "lease_expires_at": None,
                "next_eligible_at": None,
            }
        )
        state["last_confirmed_action"] = args.task_id
        state["current_stage"] = "dispatch"
        stage_id = item.get("stage_id") or (
            item.get("task_id") if item.get("task_type") == "publication-opportunity" else None
        )
        if stage_id:
            stages = ledger.get("stages", [])
            if not isinstance(stages, list):
                raise ValueError("stage-ledger.json stages must be an array")
            for stage in stages:
                if isinstance(stage, dict) and stage.get("stage_id") == stage_id:
                    stage["status"] = "completed"
                    stage["completed_at"] = timestamp
                    stage["completion_evidence"] = payload
                    if item.get("task_type") == "publication-opportunity":
                        stage["evidence_recorded"] = True
                        stage["completed_artifacts"] = ["publication-evidence.jsonl"]
                    break
    else:
        config = load_object(state_dir / "campaign-config.json")
        backoffs = config.get("automation_reliability", {}).get(
            "retry_backoff_minutes", [2, 5, 15, 30]
        )
        if not isinstance(backoffs, list) or not backoffs:
            backoffs = [2, 5, 15, 30]
        attempt = max(1, int(item.get("attempt_count", 1) or 1))
        delay = int(backoffs[min(attempt - 1, len(backoffs) - 1)])
        item.update(
            {
                "status": "retry-wait",
                "ready": False,
                "last_failure_at": timestamp,
                "last_failure_reason": args.reason or payload.get("reason"),
                "last_failure_payload": payload,
                "next_eligible_at": iso_time(now + timedelta(minutes=delay)),
                "lease_id": None,
                "lease_expires_at": None,
            }
        )
        state["current_stage"] = "recovering"
    state["updated_at"] = timestamp
    queue["updated_at"] = timestamp
    ledger["updated_at"] = timestamp
    write_runtime(state_dir, state, queue, ledger)
    append_jsonl(
        state_dir / "task-events.jsonl",
        {
            "event": args.event,
            "task_id": args.task_id,
            "recorded_at": timestamp,
            "payload": payload,
            "reason": args.reason,
            "status": item.get("status"),
        },
    )
    return {"valid": True, "task": item}


def reserve_pass(args, state_dir: Path, state: dict[str, Any], now) -> dict[str, Any]:
    require_active_consent(state_dir, state, now)
    config = load_object(state_dir / "campaign-config.json")
    queue = load_object(state_dir / "work-queue.json")
    item = find_task(queue, args.task_id)
    rules = config.get("automation_reliability", {}).get("reserve", {})
    max_pages = int(rules.get("max_pages_per_pass", 5) or 5)
    max_minutes = float(rules.get("max_minutes_per_pass", 8) or 8)
    min_yield = float(rules.get("min_qualified_yield_per_page", 0.25) or 0.25)
    cooldown = int(rules.get("low_yield_backoff_minutes", 30) or 30)
    scaling = state.setdefault("engagement_scaling", {})
    reserve = scaling.setdefault("adaptive_reserve", {})
    inspected = max(0, args.inspected)
    rejected = max(0, args.rejected)
    staleness = rejected / inspected if inspected else float(reserve.get("staleness_rate", 0) or 0)
    yield_per_page = args.qualified_found / max(1, args.pages)
    reserve["qualified_count"] = max(0, args.qualified_total)
    reserve["staleness_rate"] = round(staleness, 4)
    reserve["rejection_rate"] = round(rejected / inspected, 4) if inspected else 0
    reserve["discovery_yield_per_page"] = round(yield_per_page, 4)
    reserve["last_replenished_at"] = iso_time(now)
    passes = reserve.setdefault("pass_history", [])
    passes.append(
        {
            "completed_at": iso_time(now),
            "pages": args.pages,
            "elapsed_minutes": args.elapsed_minutes,
            "inspected": inspected,
            "qualified_found": args.qualified_found,
            "qualified_total": args.qualified_total,
            "rejected": rejected,
            "yield_per_page": round(yield_per_page, 4),
        }
    )
    reserve = recalculate_adaptive_reserve(state, config, now)
    target_reached = args.qualified_total >= int(reserve.get("target_count", 0) or 0)
    low_yield = yield_per_page < min_yield
    low_yield_streak = int(reserve.get("low_yield_streak", 0) or 0) + 1 if low_yield else 0
    reserve["low_yield_streak"] = low_yield_streak
    max_low_yield = max(1, int(rules.get("max_low_yield_passes", 2) or 2))
    limit_reached = args.pages >= max_pages or args.elapsed_minutes >= max_minutes or low_yield
    if target_reached:
        item["status"] = "completed"
        item["completed_at"] = iso_time(now)
        item["completion_reason"] = "adaptive-reserve-target-reached"
    elif limit_reached:
        item["status"] = "retry-wait"
        item["ready"] = False
        item["next_eligible_at"] = iso_time(
            now + timedelta(minutes=cooldown * min(max(1, low_yield_streak), max_low_yield))
        )
        item["last_failure_reason"] = "reserve-pass-stopping-condition"
    else:
        item["status"] = "pending"
        item["ready"] = True
    item["checkpoint"] = {
        "qualified_total": args.qualified_total,
        "target_count": reserve.get("target_count"),
        "pages": args.pages,
        "elapsed_minutes": args.elapsed_minutes,
        "yield_per_page": round(yield_per_page, 4),
    }
    item["checkpointed_at"] = iso_time(now)
    item["lease_id"] = None
    item["lease_expires_at"] = None
    state.setdefault("runtime_continuity", {})["last_heartbeat_at"] = iso_time(now)
    state["last_confirmed_action"] = f"reserve-checkpoint:{args.task_id}"
    state["current_stage"] = "dispatch" if target_reached else "adaptive-reserve"
    state["updated_at"] = iso_time(now)
    queue["updated_at"] = iso_time(now)
    write_runtime(state_dir, state, queue)
    return {
        "valid": True,
        "target_reached": target_reached,
        "stopping_condition_reached": limit_reached,
        "low_yield": low_yield,
        "reserve": reserve,
        "task": item,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state_dir", type=Path)
    parser.add_argument("--now", help="ISO timestamp used in deterministic tests")
    subparsers = parser.add_subparsers(dest="command", required=True)

    grant = subparsers.add_parser("consent-grant")
    grant.add_argument("--owner")
    grant.add_argument("--source", default="explicit-owner-confirmation")
    subparsers.add_parser("consent-revoke")

    bind = subparsers.add_parser("browser-bind")
    bind.add_argument("--device-id", required=True)
    bind.add_argument("--device-label")
    bind.add_argument("--platform")
    bind.add_argument("--identity-verified", action="store_true")
    bind.add_argument("--replace", action="store_true")

    record = subparsers.add_parser("preflight-record")
    record.add_argument("--component", required=True)
    record.add_argument("--status", choices=("passed", "failed", "unknown"), required=True)
    record.add_argument("--evidence")
    record.add_argument("--fingerprint")
    record.add_argument("--ttl-minutes", type=int)
    subparsers.add_parser("preflight-status")

    lane = subparsers.add_parser("lane-event")
    lane.add_argument("--lane", choices=("linkedin", "offline"), required=True)
    lane.add_argument("--event", choices=("transient-failure", "hard-blocker", "recovered"), required=True)
    lane.add_argument("--reason", required=True)

    continuation = subparsers.add_parser("continuation-event")
    continuation.add_argument("--event", choices=("armed", "woke", "failed"), required=True)
    continuation.add_argument("--adapter")
    continuation.add_argument("--automation-id")
    continuation.add_argument("--next-wake-at")
    continuation.add_argument("--reason")

    event = subparsers.add_parser("task-event")
    event.add_argument("--task-id", required=True)
    event.add_argument("--event", choices=("start", "checkpoint", "complete", "fail"), required=True)
    event.add_argument("--payload")
    event.add_argument("--reason")

    reserve = subparsers.add_parser("reserve-pass")
    reserve.add_argument("--task-id", default="replenish-adaptive-reserve")
    reserve.add_argument("--pages", type=int, required=True)
    reserve.add_argument("--elapsed-minutes", type=float, required=True)
    reserve.add_argument("--inspected", type=int, required=True)
    reserve.add_argument("--qualified-found", type=int, required=True)
    reserve.add_argument("--qualified-total", type=int, required=True)
    reserve.add_argument("--rejected", type=int, required=True)

    subparsers.add_parser("heartbeat")
    args = parser.parse_args()
    state_dir = args.state_dir.expanduser().resolve()
    try:
        state = load_object(state_dir / "campaign-state.json")
        now = current_time(args.now)
        if args.command == "consent-grant":
            result = consent_grant(args, state_dir, state, now)
        elif args.command == "consent-revoke":
            result = consent_revoke(state_dir, state, now)
        elif args.command == "browser-bind":
            result = browser_bind(args, state_dir, state, now)
        elif args.command == "preflight-record":
            result = preflight_record(args, state_dir, state, now)
        elif args.command == "preflight-status":
            result = preflight_status(state_dir, state, now)
        elif args.command == "lane-event":
            result = lane_event(args, state_dir, state, now)
        elif args.command == "continuation-event":
            result = continuation_event(args, state_dir, state, now)
        elif args.command == "task-event":
            result = task_event(args, state_dir, state, now)
        elif args.command == "reserve-pass":
            result = reserve_pass(args, state_dir, state, now)
        else:
            require_active_consent(state_dir, state, now)
            state.setdefault("runtime_continuity", {})["last_heartbeat_at"] = iso_time(now)
            state["updated_at"] = iso_time(now)
            write_runtime(state_dir, state)
            result = {"valid": True, "heartbeat_at": iso_time(now)}
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
