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
    reconcile_recovered_lane_continuation,
    sync_consent_snapshot,
)
from opportunity_recovery import (
    eligible_opportunities,
    next_discovery_source,
    opportunity_document,
)
from operational_output import SCRIPT as ROLLING_OUTPUT_SCRIPT

EXECUTION_SCRIPTS = ROLLING_OUTPUT_SCRIPT.parent
sys.path.insert(0, str(EXECUTION_SCRIPTS))
from rolling_output import ACTION_CAP, refresh_output  # noqa: E402

PUBLISHING_SCRIPTS = Path(__file__).resolve().parents[2] / "linkedin-publishing-operations" / "scripts"
sys.path.insert(0, str(PUBLISHING_SCRIPTS))
from publishing_ledger import record_publication_evidence  # noqa: E402


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
    existing = consent.get("operating_receipt", {})
    if consent.get("status") == "active" and isinstance(existing, dict) and existing.get("receipt_id"):
        sync_consent_snapshot(state_dir, state, now)
        write_runtime(state_dir, state)
        return {
            "valid": True,
            "already_active": True,
            "receipt_id": existing["receipt_id"],
            "scope": consent.get("scope"),
            "renewal_required": False,
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
            "operating_receipt": {
                "receipt_id": receipt_id,
                "granted_at": iso_time(now),
                "granted_by": granted_by,
                "source": args.source,
                "automation_mode": "automatic-local-workspace",
                "portable_across_model_sessions": True,
            },
            "renewal_policy": {
                "routine_renewal_required": False,
                "reload_on_every_session_start": True,
                "renew_only_when": [
                    "owner-revoked",
                    "consent-record-missing-or-invalid",
                    "verified-account-identity-changed",
                ],
            },
        }
    )
    settings = consent.setdefault("persistent_settings", [])
    for setting in (
        "campaign-start-operating-receipt",
        "campaign-lifetime-receipt-reload",
        "automatic-recovery-and-continuation",
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
        "renewal_required": False,
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
            "selection_policy": "reuse-pinned-device-directly",
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
        reconcile_recovered_lane_continuation(state, now)
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
                "setup_input_required": False,
                "active_adapter": args.adapter,
                "automation_id": args.automation_id,
                "next_wake_at": args.next_wake_at or dispatcher.get("next_wake_at"),
                "dedupe_key": f"linkedin-campaign-continuation:{state.get('campaign_id') or state_dir.name}",
                "armed_at": timestamp,
                "expiry_policy": "renew-before-host-limit-until-target-or-stop-signal",
                "renew_existing_automation": True,
                "renewal_due_before_expiry": True,
                "campaign_completion_or_stop_signal_required_to_end": True,
                "last_error": None,
            }
        )
    elif args.event == "woke":
        continuation.update(
            {
                "mode": "automatic",
                "status": "active",
                "setup_input_required": False,
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
                "setup_input_required": False,
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
        if item.get("task_type") == "six-package-replenishment":
            pipeline = load_object(state_dir / "content-pipeline.json")
            topic_candidates = pipeline.get("topic_candidates", [])
            briefs = pipeline.get("briefs", [])
            packages = pipeline.get("packages", [])
            if not all(isinstance(values, list) for values in (topic_candidates, briefs, packages)):
                raise ValueError("content pipeline candidates, briefs, and packages must be arrays")
            topic_target = int(item.get("topic_candidate_target", 12) or 12)
            package_target = int(item.get("required_package_count", item.get("inventory_target", 6)) or 6)
            ready_packages = [
                package
                for package in packages
                if isinstance(package, dict) and package.get("status") in {"ready", "validated"}
            ]
            missing_counts = {
                "topic_candidates": max(0, topic_target - len(topic_candidates)),
                "briefs": max(0, package_target - len(briefs)),
                "ready_packages": max(0, package_target - len(ready_packages)),
            }
            if any(missing_counts.values()):
                raise ValueError(
                    "six-package completion requires the full configured pipeline before closing: "
                    f"need {topic_target} topic candidates, {package_target} briefs, and "
                    f"{package_target} ready packages; missing {missing_counts}"
                )
        if item.get("task_type") in {"publication-opportunity", "publication-execution"}:
            region = payload.get("region") or item.get("region")
            required = {"post_id", "post_url"}
            missing = [key for key in required if not payload.get(key)]
            if not region:
                missing.append("region")
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
                "schema_version": "2.0",
                "campaign_id": state.get("campaign_id"),
                "content_day_local": day,
                "region": region,
                "post_id": payload["post_id"],
                "post_url": payload["post_url"],
                "published_at": payload.get("published_at") or timestamp,
                "verified": True,
                "task_id": item.get("task_id"),
                "package_id": item.get("package_id") or payload.get("package_id"),
                "package_path": item.get("package_path"),
                "publication_kind": item.get("publication_kind", "normal"),
            }
            publication_result = record_publication_evidence(state_dir, evidence, now)
            refreshed_state = load_object(state_dir / "campaign-state.json")
            refreshed_publishing = refreshed_state.get("publishing", {})
            if isinstance(refreshed_publishing, dict):
                publishing.update(refreshed_publishing)
            ids = publishing.setdefault("published_post_ids", [])
            if payload["post_id"] not in ids:
                ids.append(payload["post_id"])
            publishing["last_publication_at"] = evidence["published_at"]
            if item.get("publication_kind") == "recovery":
                publishing["recovery_posts_published"] = int(
                    publishing.get("recovery_posts_published", 0) or 0
                ) + 1
                publishing["recovery_package"] = None
                analytics_id = f"recovery-analytics-{day}-{payload['post_id']}"
                if not any(
                    isinstance(candidate, dict) and candidate.get("task_id") == analytics_id
                    for candidate in queue.get("items", [])
                ):
                    queue["items"].append(
                        {
                            "task_id": analytics_id,
                            "task_type": "performance-recovery-analytics",
                            "lane": "offline",
                            "priority": 3,
                            "status": "pending",
                            "ready": True,
                            "requires_linkedin": False,
                            "content_day_local": day,
                            "post_id": payload["post_id"],
                            "required_artifacts": ["daily-analytics.jsonl", "opportunity-health.jsonl"],
                            "idempotency_key": f"recovery-analytics:{day}:{payload['post_id']}",
                        }
                    )
            else:
                publishing["normal_posts_published"] = min(
                    6,
                    int(publishing.get("normal_posts_published", 0) or 0) + 1,
                )
            item["publication_result"] = publication_result
        if item.get("task_type") == "rolling-output-evaluation":
            decision_name = payload.get("decision")
            if decision_name not in {"publish-now", "continue-investigation"}:
                raise ValueError(
                    "rolling output evaluation requires publish-now or continue-investigation"
                )
            package_id = str(payload.get("package_id") or item.get("package_id") or "")
            pipeline_path = state_dir / "content-pipeline.json"
            pipeline = load_object(pipeline_path)
            package = next(
                (
                    candidate for candidate in pipeline.get("packages", [])
                    if isinstance(candidate, dict) and candidate.get("package_id") == package_id
                ),
                None,
            )
            if package is None:
                raise ValueError(f"unknown publication package: {package_id}")
            attempt = int(item.get("evaluation_attempt", 1) or 1)
            decision_record = {
                "decision": decision_name,
                "attempt": attempt,
                "evaluated_at": timestamp,
                "evidence": payload.get("evidence") or {},
            }
            if decision_name == "publish-now":
                score = payload.get("opportunity_score")
                if isinstance(score, bool) or not isinstance(score, (int, float)) or score < 65:
                    raise ValueError("publish-now requires opportunity_score of at least 65")
                decision_record["opportunity_score"] = float(score)
                decision_record["selected_at"] = payload.get("selected_at") or timestamp
            else:
                next_evaluation = parse_time(payload.get("next_evaluation_at"))
                if next_evaluation is None or next_evaluation <= now:
                    raise ValueError(
                        "continue-investigation requires an exact future next_evaluation_at"
                    )
                decision_record["next_evaluation_at"] = iso_time(next_evaluation)
                decision_record["reason"] = payload.get("reason") or "opportunity-below-threshold"
            package["publication_decision"] = decision_record
            atomic_write(pipeline_path, pipeline)
        if item.get("task_type") == "preflight" and payload.get("preflight_passed") is not True:
            raise ValueError("preflight completion requires preflight_passed=true")
        if item.get("task_type") == "publication-queue-building":
            source_id = item.get("source_publication_task_id")
            if source_id:
                find_task(queue, str(source_id))["engagement_queue_ready"] = True
        if item.get("task_type") == "performance-recovery-content":
            required = {"package_path", "publication_score", "fresh_source", "distinct_angle", "distinct_pillar_or_format"}
            missing = [key for key in required if payload.get(key) in (None, "", False)]
            if missing:
                raise ValueError(
                    "recovery content completion requires package, score, fresh source, distinct angle, and distinct pillar or format"
                )
            score = float(payload["publication_score"])
            if score < 65:
                raise ValueError("recovery publication score must be at least 65")
            publishing = state.setdefault("publishing", {})
            existing_package = publishing.get("recovery_package")
            if isinstance(existing_package, dict) and existing_package.get("status") == "ready":
                raise ValueError("only one unpublished recovery package may exist")
            publishing["recovery_package"] = {
                "status": "ready",
                "package_path": payload["package_path"],
                "publication_score": score,
                "fresh_source": payload["fresh_source"],
                "distinct_angle": payload["distinct_angle"],
                "distinct_pillar_or_format": payload["distinct_pillar_or_format"],
                "region": payload.get("region", "adaptive-recovery"),
                "prepared_at": timestamp,
                "content_day_local": item.get("content_day_local"),
            }
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
            item.get("task_id")
            if item.get("task_type") in {"publication-opportunity", "publication-execution"}
            else None
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
                    if item.get("task_type") in {"publication-opportunity", "publication-execution"}:
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


def opportunity_pass(args, state_dir: Path, state: dict[str, Any], now) -> dict[str, Any]:
    """Persist one source attempt and canonical candidates, then rotate on low yield."""
    require_active_consent(state_dir, state, now)
    config = load_object(state_dir / "campaign-config.json")
    queue = load_object(state_dir / "work-queue.json")
    item = find_task(queue, args.task_id)
    source = args.source or item.get("discovery_source")
    if not source:
        raise ValueError("opportunity pass requires a discovery source")
    document = opportunity_document(state_dir, str(state.get("campaign_id") or ""))
    incoming: list[dict[str, Any]] = []
    if args.candidates_file:
        payload = load_object(args.candidates_file.expanduser().resolve())
        incoming = payload.get("opportunities", payload.get("candidates", []))
        if not isinstance(incoming, list):
            raise ValueError("candidate input must contain an opportunities or candidates array")
    records = document.setdefault("opportunities", [])
    by_id = {
        str(record.get("candidate_id")): record
        for record in records
        if isinstance(record, dict) and record.get("candidate_id")
    }
    accepted = 0
    rejection_reasons: dict[str, int] = {}
    for candidate in incoming:
        if not isinstance(candidate, dict) or not candidate.get("candidate_id"):
            continue
        candidate_id = str(candidate["candidate_id"])
        current = by_id.get(candidate_id)
        if current and current.get("status") == "executed":
            continue
        lane = candidate.get("lane", "proactive")
        score = candidate.get("score", candidate.get("action_score"))
        identity = (
            candidate.get("candidate_identity")
            or candidate.get("target_id")
            or candidate.get("profile_url")
            or candidate_id
        )
        complete = bool(
            identity
            and candidate.get("action_available", True) is True
            and (lane == "direct-inbound" or (
                isinstance(score, (int, float))
                and not isinstance(score, bool)
                and candidate.get("cooldown_passed") is True
                and candidate.get("action_type")
                and (
                    candidate.get("target_status") != "new"
                    or isinstance(candidate.get("follower_count"), (int, float))
                    and not isinstance(candidate.get("follower_count"), bool)
                )
            ))
        )
        requested_status = candidate.get("status", "qualified")
        lifecycle_status = requested_status if requested_status not in {"qualified", "ready"} or complete else "needs-revalidation"
        normalized = {
            **(current or {}),
            **candidate,
            "candidate_id": candidate_id,
            "candidate_identity": identity,
            "source": candidate.get("source") or source,
            "lane": lane,
            "score": score,
            "active_gate_tier": state.get("opportunity_recovery", {}).get("mode", "normal"),
            "post_freshness": candidate.get("post_freshness"),
            "cooldown_passed": candidate.get("cooldown_passed") is True,
            "follower_count": candidate.get("follower_count"),
            "action_type": candidate.get("action_type"),
            "status": lifecycle_status,
            "lifecycle_status": lifecycle_status,
            "discovered_at": candidate.get("discovered_at") or iso_time(now),
            "expires_at": candidate.get("expires_at") or candidate.get("expiry"),
            "evidence": candidate.get("evidence", {}),
        }
        if current:
            current.update(normalized)
        else:
            records.append(normalized)
            by_id[candidate_id] = normalized
        if normalized["status"] in {"qualified", "ready"}:
            accepted += 1
        else:
            reason = str(
                candidate.get("rejection_reason")
                or candidate.get("excluded_reason")
                or normalized["status"]
            )
            rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
    document["updated_at"] = iso_time(now)
    atomic_write(state_dir / "engagement-opportunities.json", document)
    inspected = max(0, args.inspected)
    rejected = max(0, args.rejected)
    stale = max(0, args.stale)
    yield_rate = accepted / max(1, inspected)
    recovery = state.setdefault("opportunity_recovery", {})
    source_history = recovery.setdefault("source_performance", {})
    stats = source_history.setdefault(str(source), {})
    stats["attempts"] = int(stats.get("attempts", 0) or 0) + 1
    stats["inspected"] = int(stats.get("inspected", 0) or 0) + inspected
    stats["accepted_candidates"] = int(stats.get("accepted_candidates", 0) or 0) + accepted
    stats["rejected"] = int(stats.get("rejected", 0) or 0) + rejected
    recorded_reasons = stats.setdefault("rejection_reasons", {})
    for reason, count in rejection_reasons.items():
        recorded_reasons[reason] = int(recorded_reasons.get(reason, 0) or 0) + count
    stats["stale"] = int(stats.get("stale", 0) or 0) + stale
    stats["last_yield"] = round(yield_rate, 4)
    stats["last_attempt_at"] = iso_time(now)
    recovery["last_discovery_source"] = str(source)
    low_yield = yield_rate < float(
        config.get("automation_reliability", {}).get("reserve", {}).get("min_qualified_yield_per_page", 0.25)
    )
    cooldown = int(
        config.get("automation_reliability", {}).get("reserve", {}).get("low_yield_backoff_minutes", 30)
        or 30
    )
    not_before = now + timedelta(minutes=cooldown if low_yield else 1)
    stats["backoff_until"] = iso_time(not_before) if low_yield else None
    recovery["source_not_before"] = None
    recovery["next_discovery_source"] = next_discovery_source(state, config, now)
    reserve = state.setdefault("engagement_scaling", {}).setdefault("adaptive_reserve", {})
    eligible = eligible_opportunities(document, state, config, now)
    reserve["qualified_count"] = len(eligible)
    reserve["count_source"] = "engagement-opportunities.json"
    reserve["discovery_yield_per_page"] = round(yield_rate, 4)
    reserve["staleness_rate"] = round(stale / max(1, inspected), 4)
    reserve["rejection_rate"] = round(rejected / max(1, inspected), 4)
    reserve.setdefault("pass_history", []).append(
        {
            "completed_at": iso_time(now),
            "source": source,
            "inspected": inspected,
            "accepted_candidates": accepted,
            "rejected": rejected,
            "rejection_reasons": rejection_reasons,
            "stale": stale,
            "yield": round(yield_rate, 4),
            "not_before": iso_time(not_before),
            "next_source": recovery["next_discovery_source"],
        }
    )
    item.update(
        {
            "status": "completed",
            "ready": False,
            "completed_at": iso_time(now),
            "completion_reason": "opportunity-generation-pass-recorded",
            "not_before": iso_time(not_before),
            "next_discovery_source": recovery["next_discovery_source"],
            "lease_id": None,
            "lease_expires_at": None,
        }
    )
    state["current_stage"] = "dispatch"
    state["updated_at"] = iso_time(now)
    queue["updated_at"] = iso_time(now)
    write_runtime(state_dir, state, queue)
    append_jsonl(
        state_dir / "signal-events.jsonl",
        {
            "event": "engagement-opportunity-generation",
            "recorded_at": iso_time(now),
            "source": source,
            "inspected": inspected,
            "accepted": accepted,
            "rejected": rejected,
            "stale": stale,
            "not_before": iso_time(not_before),
        },
    )
    return {
        "valid": True,
        "source": source,
        "accepted": accepted,
        "canonical_eligible_count": len(eligible),
        "low_yield": low_yield,
        "not_before": iso_time(not_before),
        "next_source": recovery["next_discovery_source"],
        "task": item,
    }


def burst_complete(args, state_dir: Path, state: dict[str, Any], now) -> dict[str, Any]:
    """Atomically close a burst, candidate lifecycles, and budget accounting."""
    require_active_consent(state_dir, state, now)
    queue = load_object(state_dir / "work-queue.json")
    item = find_task(queue, args.task_id)
    if item.get("status") == "completed":
        return {"valid": True, "idempotent": True, "task": item}
    executed_ids = [value for value in args.executed_candidate_ids.split(",") if value]
    document = opportunity_document(state_dir, str(state.get("campaign_id") or ""))
    by_id = {
        str(record.get("candidate_id")): record
        for record in document.get("opportunities", [])
        if isinstance(record, dict) and record.get("candidate_id")
    }
    output_before = refresh_output(state_dir, now, write=False)
    scaling = state.setdefault("engagement_scaling", {})
    base_used = int(output_before["actions"]["rolling_24h_actions"])
    overage = int(output_before["actions"]["direct_inbound_replies"])
    source_history = state.setdefault("opportunity_recovery", {}).setdefault("source_performance", {})
    executed: list[str] = []
    executed_sources: list[str] = []
    for candidate_id in executed_ids:
        record = by_id.get(candidate_id)
        if record is None or record.get("status") == "executed":
            continue
        lane = record.get("lane", "proactive")
        if lane == "direct-inbound":
            overage += 1
            budget_class = "direct-inbound-outside-cap"
        elif base_used < ACTION_CAP:
            base_used += 1
            budget_class = "rolling-base"
        else:
            continue
        record.update(
            {
                "status": "executed",
                "executed_at": iso_time(now),
                "budget_class": budget_class,
                "lifecycle_status": "executed",
                "relationship_strength": min(
                    1.0,
                    float(record.get("relationship_strength", 0) or 0)
                    + (0.10 if args.replies_generated else 0.03),
                ),
                "relationship_evidence": {
                    "last_burst_id": args.task_id,
                    "last_action_at": iso_time(now),
                },
            }
        )
        source = str(record.get("source") or "unknown")
        stats = source_history.setdefault(source, {})
        stats["actions_executed"] = int(stats.get("actions_executed", 0) or 0) + 1
        executed_sources.append(source)
        executed.append(candidate_id)
        append_jsonl(
            state_dir / "interaction-log.jsonl",
            {
                "schema_version": "2.0",
                "action_id": f"{args.task_id}:{candidate_id}",
                "candidate_id": candidate_id,
                "lane": lane,
                "action_type": record.get("action_type"),
                "triggering_signal": record.get("triggering_signal") or record.get("source"),
                "relationship_strength": record.get("relationship_strength", 0),
                "scheduling_rationale": "executed from canonical v6 engagement burst",
                "budget_class": budget_class,
                "recorded_at": iso_time(now),
                "executed_at": iso_time(now),
                "confirmed": True,
                "external_action_occurred": True,
            },
        )
    if executed_sources:
        primary_stats = source_history.setdefault(executed_sources[0], {})
        primary_stats["replies_generated"] = int(primary_stats.get("replies_generated", 0) or 0) + args.replies_generated
        primary_stats["profile_views"] = int(primary_stats.get("profile_views", 0) or 0) + args.profile_views
        primary_stats["follower_outcomes"] = int(primary_stats.get("follower_outcomes", 0) or 0) + args.follower_outcomes
    scaling["base_actions_used"] = min(ACTION_CAP, base_used)
    scaling["direct_reply_overage"] = overage
    scaling.setdefault("burst_history", []).append(
        {
            "burst_id": args.task_id,
            "completed_at": iso_time(now),
            "actions_executed": len(executed),
            "candidate_ids": executed,
            "replies_generated": args.replies_generated,
            "profile_views": args.profile_views,
            "follower_outcomes": args.follower_outcomes,
        }
    )
    scaling["concentration_state"] = {
        "current_penalty": min(1.0, len(executed) / 10),
        "last_burst_at": iso_time(now),
        "decay_trigger": "observed-engagement-and-platform-feedback",
    }
    recovery = state.setdefault("opportunity_recovery", {})
    recovery["next_reevaluation_trigger"] = "immediate-after-engagement-burst"
    recovery["next_opportunity_prediction"] = {
        "basis": "canonical-remaining-supply-and-source-yield",
        "canonical_remaining": sum(
            1 for record in document.get("opportunities", [])
            if isinstance(record, dict) and record.get("status") in {"qualified", "ready"}
        ),
        "predicted_at": iso_time(now),
    }
    item.update(
        {
            "status": "completed",
            "completed_at": iso_time(now),
            "completion_reason": "engagement-burst-recorded",
            "executed_candidate_ids": executed,
            "lease_id": None,
            "lease_expires_at": None,
        }
    )
    document["updated_at"] = iso_time(now)
    atomic_write(state_dir / "engagement-opportunities.json", document)
    config = load_object(state_dir / "campaign-config.json")
    reserve = scaling.setdefault("adaptive_reserve", {})
    reserve["qualified_count"] = len(eligible_opportunities(document, state, config, now))
    reserve["count_source"] = "engagement-opportunities.json"
    state["current_stage"] = "dispatch"
    state["last_confirmed_action"] = f"burst:{args.task_id}"
    state["updated_at"] = iso_time(now)
    queue["updated_at"] = iso_time(now)
    write_runtime(state_dir, state, queue)
    rolling = refresh_output(state_dir, now, write=True)
    return {
        "valid": True,
        "executed_candidate_ids": executed,
        "rolling_24h_actions": rolling["actions"]["rolling_24h_actions"],
        "rolling_action_target": rolling["actions"]["target"],
        "rolling_action_cap": rolling["actions"]["hard_cap"],
        "direct_inbound_replies": rolling["actions"]["direct_inbound_replies"],
        "canonical_eligible_count": reserve["qualified_count"],
        "task": item,
    }


def reserve_pass(args, state_dir: Path, state: dict[str, Any], now) -> dict[str, Any]:
    require_active_consent(state_dir, state, now)
    config = load_object(state_dir / "campaign-config.json")
    queue = load_object(state_dir / "work-queue.json")
    item = find_task(queue, args.task_id)
    source = item.get("discovery_source")
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
    canonical = opportunity_document(state_dir, str(state.get("campaign_id") or ""))
    reserve["qualified_count"] = len(eligible_opportunities(canonical, state, config, now))
    reserve["count_source"] = "engagement-opportunities.json"
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
    reserve = recalculate_adaptive_reserve(state, config, now, state_dir)
    target_reached = reserve["qualified_count"] >= int(reserve.get("target_count", 0) or 0)
    low_yield = yield_per_page < min_yield
    low_yield_streak = int(reserve.get("low_yield_streak", 0) or 0) + 1 if low_yield else 0
    reserve["low_yield_streak"] = low_yield_streak
    max_low_yield = max(1, int(rules.get("max_low_yield_passes", 2) or 2))
    limit_reached = args.pages >= max_pages or args.elapsed_minutes >= max_minutes or low_yield
    next_eligible_at = now + timedelta(
        minutes=cooldown * min(max(1, low_yield_streak), max_low_yield)
    )
    if source:
        recovery = state.setdefault("opportunity_recovery", {})
        source_history = recovery.setdefault("source_performance", {})
        stats = source_history.setdefault(str(source), {})
        stats["attempts"] = int(stats.get("attempts", 0) or 0) + 1
        stats["inspected"] = int(stats.get("inspected", 0) or 0) + inspected
        stats["accepted_candidates"] = int(stats.get("accepted_candidates", 0) or 0) + max(
            0, args.qualified_found
        )
        stats["rejected"] = int(stats.get("rejected", 0) or 0) + rejected
        stats["last_yield"] = round(yield_per_page, 4)
        stats["last_attempt_at"] = iso_time(now)
        stats["backoff_until"] = iso_time(next_eligible_at) if low_yield else None
        recovery["last_discovery_source"] = str(source)
        recovery["next_discovery_source"] = next_discovery_source(state, config, now)
    if target_reached:
        item["status"] = "completed"
        item["completed_at"] = iso_time(now)
        item["completion_reason"] = "adaptive-reserve-target-reached"
    elif limit_reached:
        item["status"] = "completed" if source else "retry-wait"
        item["ready"] = False
        item["next_eligible_at"] = iso_time(next_eligible_at) if not source else None
        item["not_before"] = iso_time(next_eligible_at)
        item["completed_at"] = iso_time(now) if source else None
        item["completion_reason"] = "opportunity-generation-pass-recorded" if source else None
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
    state["current_stage"] = "dispatch" if source or target_reached else "adaptive-reserve"
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

    opportunity = subparsers.add_parser("opportunity-pass")
    opportunity.add_argument("--task-id", required=True)
    opportunity.add_argument("--source")
    opportunity.add_argument("--inspected", type=int, required=True)
    opportunity.add_argument("--rejected", type=int, default=0)
    opportunity.add_argument("--stale", type=int, default=0)
    opportunity.add_argument("--candidates-file", type=Path)

    burst = subparsers.add_parser("burst-complete")
    burst.add_argument("--task-id", required=True)
    burst.add_argument("--executed-candidate-ids", required=True)
    burst.add_argument("--replies-generated", type=int, default=0)
    burst.add_argument("--profile-views", type=int, default=0)
    burst.add_argument("--follower-outcomes", type=int, default=0)

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
        elif args.command == "opportunity-pass":
            result = opportunity_pass(args, state_dir, state, now)
        elif args.command == "burst-complete":
            result = burst_complete(args, state_dir, state, now)
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
