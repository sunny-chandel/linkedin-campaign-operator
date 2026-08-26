#!/usr/bin/env python3
"""Add current safe defaults and artifacts to an existing campaign directory."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runtime_state import current_time, reconcile_runtime


def merge_missing(current: Any, defaults: Any) -> tuple[Any, bool]:
    if not isinstance(current, dict) or not isinstance(defaults, dict):
        return current, False
    changed = False
    merged = dict(current)
    for key, default_value in defaults.items():
        if key not in merged:
            merged[key] = default_value
            changed = True
        elif isinstance(merged[key], dict) and isinstance(default_value, dict):
            merged_value, nested_changed = merge_missing(merged[key], default_value)
            merged[key] = merged_value
            changed = changed or nested_changed
    return merged, changed


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
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


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state_dir", type=Path)
    parser.add_argument("--now", help="ISO timestamp used in deterministic tests")
    args = parser.parse_args()

    state_dir = args.state_dir.expanduser().resolve()
    config_path = state_dir / "campaign-config.json"
    if not config_path.is_file():
        parser.error(f"missing existing campaign configuration: {config_path}")

    assets_dir = Path(__file__).resolve().parent.parent / "assets"
    defaults = load_object(assets_dir / "campaign-config.template.json")
    config = load_object(config_path)
    original_config = json.loads(json.dumps(config))
    campaign_id = config.get("campaign_id")
    if not isinstance(campaign_id, str) or not campaign_id:
        parser.error("campaign-config.json requires a campaign_id before migration")

    legacy_fixed_keys = {
        "windows_per_day",
        "max_actions_per_window",
        "gap_clusters_per_day",
        "max_action_clusters_per_day",
        "max_actions_per_cluster",
        "max_actions_per_day",
        "min_proactive_cluster_gap_minutes",
    }
    config["schema_version"] = "1.2"
    fixed = config.setdefault("fixed_rules", {})
    for key in legacy_fixed_keys:
        fixed.pop(key, None)
    fixed.update(
        {
            "posts_per_day": 2,
            "prepared_packages_per_content_day": 2,
            "max_actions_per_burst": 10,
            "base_actions_per_day": 100,
            "direct_reply_overage_allowed": True,
            "new_target_min_followers": 3000,
            "cooldown_hours": 72,
            "max_proactive_actions_per_person_per_7d": 2,
        }
    )
    engagement = config.setdefault("engagement_optimization", {})
    engagement.pop("clusters", None)
    adaptive_dispatch = config.setdefault("adaptive_dispatch", {})
    priority_order = adaptive_dispatch.get("priority_order")
    if isinstance(priority_order, list) and priority_order:
        adaptive_dispatch["priority_order"] = [
            "technical-session-or-identity-recovery",
            *priority_order[1:],
        ]
    merged, merged_missing = merge_missing(config, defaults)
    merged.setdefault("publishing_optimization", {}).setdefault(
        "production_priority_window", {}
    )["timezone"] = merged.get("timezone", "UTC")
    changed = merged_missing or merged != original_config
    if changed:
        atomic_write_json(config_path, merged)
    config = merged

    state_path = state_dir / "campaign-state.json"
    state_updated = False
    if state_path.is_file():
        state_defaults = load_object(assets_dir / "campaign-state.template.json")
        state = load_object(state_path)
        state["schema_version"] = "1.2"
        old_scaling = state.get("engagement_scaling", {})
        if not isinstance(old_scaling, dict):
            old_scaling = {}
        legacy_today = state.get("today", {})
        if not isinstance(legacy_today, dict):
            legacy_today = {}
        legacy_clusters = old_scaling.get("completed_clusters", [])
        if not isinstance(legacy_clusters, list):
            legacy_clusters = []
        base_actions_used = old_scaling.get(
            "base_actions_used", old_scaling.get("actions_executed_today", 0)
        )
        if isinstance(base_actions_used, bool) or not isinstance(base_actions_used, int):
            base_actions_used = 0
        burst_history = old_scaling.get("burst_history", [])
        if not isinstance(burst_history, list):
            burst_history = []
        existing_legacy_ids = {
            item.get("legacy_cluster_id") for item in burst_history if isinstance(item, dict)
        }
        for cluster_id in legacy_clusters:
            if cluster_id not in existing_legacy_ids:
                burst_history.append(
                    {
                        "burst_id": f"legacy-{cluster_id}",
                        "legacy_cluster_id": cluster_id,
                        "status": "completed-before-v0.5.0",
                    }
                )
        state["engagement_scaling"] = {
            "budget_day_local": old_scaling.get("budget_day_local") or old_scaling.get("budget_day_ist") or legacy_today.get("date_ist"),
            "base_daily_ceiling": 100,
            "base_actions_used": min(max(base_actions_used, 0), 100),
            "direct_reply_overage": max(int(old_scaling.get("direct_reply_overage", 0) or 0), 0),
            "burst_history": burst_history,
            "concentration_state": old_scaling.get("concentration_state", {}),
            "regional_opportunity_state": old_scaling.get("regional_opportunity_state", {}),
            "adaptive_reserve": old_scaling.get(
                "adaptive_reserve",
                {
                    "forecast_bursts": 2,
                    "target_count": 0,
                    "qualified_count": 0,
                    "staleness_rate": None,
                    "rejection_rate": None,
                    "expected_burst_size": 5,
                    "discovery_yield_per_page": None,
                    "pass_history": [],
                    "last_replenished_at": None,
                },
            ),
            "recovery_level": old_scaling.get("recovery_level", "adaptive"),
        }
        today = state.get("today", {})
        if not isinstance(today, dict):
            today = {}
        published_count = sum(
            bool(today.get(key))
            for key in ("window_2_india_published", "window_4_us_central_published")
        )
        package_count = (
            0
            if published_count >= 2
            else min(sum(1 for _ in state_dir.glob("**/publication-package*.json")), 2)
        )
        publishing = state.get("publishing", {})
        if not isinstance(publishing, dict):
            publishing = {}
        publishing.update(
            {
                "content_day_local": (
                    publishing.get("content_day_local")
                    or publishing.get("content_day_ist")
                    or today.get("date_ist")
                ),
                "content_day_ist": (
                    publishing.get("content_day_local")
                    or publishing.get("content_day_ist")
                    or today.get("date_ist")
                ),
                "packages_required": 2,
                "packages_ready": min(max(int(publishing.get("packages_ready", package_count) or 0), 0), 2),
                "posts_published": min(max(int(publishing.get("posts_published", published_count) or 0), 0), 2),
                "published_post_ids": publishing.get("published_post_ids", []),
                "last_publication_at": publishing.get("last_publication_at"),
                "current_cannibalization_signal": publishing.get("current_cannibalization_signal"),
            }
        )
        state["publishing"] = publishing
        merged_state, state_updated = merge_missing(state, state_defaults)
        state_updated = state_updated or merged_state != load_object(state_path)
        if state_updated:
            atomic_write_json(state_path, merged_state)
        state = merged_state

    consent_path = state_dir / "consent-record.json"
    consent_updated = False
    if consent_path.is_file():
        consent = load_object(consent_path)
        required_settings = [
            "automated-mode",
            "adaptive-100-base-action-ceiling",
            "continuous-24-hour-dispatch",
            "direct-inbound-overage",
            "fully-dynamic-publishing",
            "automatic-profile-watermark",
            "permanent-dominant-gif-learning-deletion",
            "one-time-high-value-consent",
            "campaign-lifetime-consent-reload",
            "automatic-recovery-without-routine-questions",
        ]
        current_settings = consent.get("persistent_settings", [])
        if not isinstance(current_settings, list):
            current_settings = []
        current_settings = [
            value for value in current_settings if value != "adaptive-80-action-ceiling"
        ]
        merged_settings = list(dict.fromkeys([*current_settings, *required_settings]))
        receipt = consent.get("authorization_receipt", {})
        receipt_missing = not isinstance(receipt, dict) or not receipt.get("receipt_id")
        owner = consent.get("owner", {})
        owner_name = owner.get("display_name") if isinstance(owner, dict) else None
        needs_update = (
            consent.get("consent_version") != "2.0"
            or consent.get("schema_version") != "2.0"
            or merged_settings != current_settings
            or (consent.get("status") == "active" and receipt_missing)
        )
        if needs_update:
            consent["schema_version"] = "2.0"
            consent["consent_version"] = "2.0"
            consent["scope"] = "campaign-lifetime"
            consent["persistent_settings"] = merged_settings
            approved = consent.get("approved_action_classes", [])
            if not isinstance(approved, list):
                approved = []
            consent["approved_action_classes"] = list(
                dict.fromkeys([*approved, "adaptive-scheduling", "signal-reciprocity"])
            )
            if consent.get("status") == "active" and receipt_missing:
                if not owner_name or owner_name == "replace-me":
                    consent["status"] = "pending"
                else:
                    granted_at = consent.get("activated_at") or datetime.now(timezone.utc).isoformat()
                    consent["activated_at"] = granted_at
                    consent["authorization_receipt"] = {
                        "receipt_id": f"consent-{campaign_id}-migrated",
                        "granted_at": granted_at,
                        "granted_by": owner_name,
                        "source": "migrated-existing-explicit-owner-consent",
                        "automation_mode": "fully-automated",
                        "portable_across_model_sessions": True,
                    }
            consent["reconfirmation_policy"] = {
                "routine_reconfirmation_required": False,
                "reload_on_every_session_start": True,
                "reask_only_when": [
                    "owner-revoked",
                    "consent-record-missing-or-invalid",
                    "verified-account-identity-changed",
                ],
            }
            atomic_write_json(consent_path, consent)
            consent_updated = True

    created: list[str] = []
    artifacts = {
        "brand-profile.json": {
            "schema_version": "1.0",
            "campaign_id": campaign_id,
            "profile": {},
            "custom_overrides": {},
            "identity_hash": None,
            "generated_at": None,
        },
        "watermark-manifest.json": {
            "schema_version": "1.0",
            "campaign_id": campaign_id,
            "identity_hash": None,
            "claude_design_project": None,
            "variants": [],
            "last_verified_at": None,
        },
        "creator-registry.json": {
            "schema_version": "1.0",
            "campaign_id": campaign_id,
            "core": [],
            "rotating": [],
            "last_observed_at": None,
        },
        "gif-reference-index.json": {
            "schema_version": "1.0",
            "campaign_id": campaign_id,
            "references": [],
        },
        "creative-pattern-library.json": {
            "schema_version": "1.0",
            "campaign_id": campaign_id,
            "patterns": [],
        },
        "gif-creative-spec.json": {
            "schema_version": "1.0",
            "campaign_id": campaign_id,
            "selected_reference_id": None,
            "selected_pattern_id": None,
            "validation_status": "not-generated",
        },
        "subscription-inventory.json": {
            "schema_version": "1.0",
            "campaign_id": campaign_id,
            "generated_at": None,
            "subscription": {},
            "features": [],
        },
        "subscription-utilization-plan.json": {
            "schema_version": "1.0",
            "campaign_id": campaign_id,
            "generated_at": None,
            "features": [],
            "summary": {},
        },
        "work-queue.json": {
            "schema_version": "1.0",
            "campaign_id": campaign_id,
            "updated_at": None,
            "items": [],
        },
        "stage-ledger.json": {
            "schema_version": "1.0",
            "campaign_id": campaign_id,
            "updated_at": None,
            "stages": [],
        },
    }
    for name, initial in artifacts.items():
        path = state_dir / name
        if not path.exists():
            atomic_write_json(path, initial)
            created.append(name)
    results = state_dir / "subscription-results.jsonl"
    if not results.exists():
        results.touch()
        created.append(results.name)
    for name in (
        "signal-events.jsonl",
        "schedule-decisions.jsonl",
        "publication-evidence.jsonl",
        "task-events.jsonl",
        "recovery-events.jsonl",
    ):
        path = state_dir / name
        if not path.exists():
            path.touch()
            created.append(path.name)

    algorithm_path = state_dir / "working-algorithm-model.json"
    algorithm_defaults = {
        "schema_version": "1.1",
        "campaign_id": campaign_id,
        "version": "0.2",
        "strategy_weights": {"proven": 70, "promising": 20, "exploration": 10},
        "scheduling_models": {
            "publication_timing": {"mode": "evidence-adaptive", "observations": []},
            "response_latency": {"mode": "evidence-adaptive", "observations": []},
            "regional_opportunity": {"mode": "evidence-adaptive", "observations": []},
            "concentration": {"mode": "evidence-adaptive", "observations": []},
            "candidate_staleness": {"mode": "evidence-adaptive", "observations": []},
        },
        "hypotheses": [],
    }
    if algorithm_path.exists():
        algorithm = load_object(algorithm_path)
        merged_algorithm, algorithm_updated = merge_missing(algorithm, algorithm_defaults)
        merged_algorithm["schema_version"] = "1.1"
        merged_algorithm["version"] = "0.2"
        if algorithm_updated or merged_algorithm != algorithm:
            atomic_write_json(algorithm_path, merged_algorithm)
    else:
        atomic_write_json(algorithm_path, algorithm_defaults)
        created.append(algorithm_path.name)

    state = load_object(state_path) if state_path.is_file() else {}
    queue_path = state_dir / "work-queue.json"
    queue = load_object(queue_path)
    items = queue.get("items", [])
    if not isinstance(items, list):
        items = []
    existing_task_ids = {item.get("task_id") for item in items if isinstance(item, dict)}
    reserve = state.get("engagement_scaling", {}).get("adaptive_reserve", {})
    if reserve.get("qualified_count", 0) < reserve.get("target_count", 0) or not reserve.get("qualified_count"):
        if "replenish-adaptive-reserve" not in existing_task_ids:
            items.append(
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
    publishing = state.get("publishing", {})
    if publishing.get("packages_ready", 0) < 2 and "prepare-two-packages" not in existing_task_ids:
        items.append(
            {
                "task_id": "prepare-two-packages",
                "task_type": "two-package-production",
                "lane": "offline",
                "priority": 7,
                "status": "pending",
                "ready": True,
                "requires_linkedin": False,
                "target_scope": "next-content-day" if publishing.get("posts_published", 0) >= 2 else "current-content-day",
                "required_regions": config.get("publishing_optimization", {}).get(
                    "required_regions", ["india", "us-central"]
                ),
                "required_package_count": len(
                    config.get("publishing_optimization", {}).get(
                        "required_regions", ["india", "us-central"]
                    )
                ),
                "no_third_package": True,
            }
        )
    analytics_path = state_dir / "daily-analytics.jsonl"
    learning_path = state_dir / "learning-ledger.jsonl"
    analytics_debt = analytics_path.exists() and analytics_path.stat().st_size > 0 and (
        not learning_path.exists() or '"stage": "analytics-learning"' not in learning_path.read_text(encoding="utf-8")
    )
    if analytics_debt and "analytics-backfill" not in existing_task_ids:
        items.append(
            {
                "task_id": "analytics-backfill",
                "task_type": "mandatory-stage-recovery",
                "lane": "offline",
                "priority": 4,
                "status": "pending",
                "ready": True,
                "requires_linkedin": False,
            }
        )
    queue["items"] = items
    atomic_write_json(queue_path, queue)

    ledger_path = state_dir / "stage-ledger.json"
    ledger = load_object(ledger_path)
    stages = ledger.get("stages", [])
    if not isinstance(stages, list):
        stages = []
    stage_ids = {stage.get("stage_id") for stage in stages if isinstance(stage, dict)}
    if analytics_debt and "analytics-backfill" not in stage_ids:
        stages.append(
            {
                "stage_id": "analytics-backfill",
                "stage_type": "analytics",
                "status": "missed-recovering",
                "required_artifacts": ["daily-analytics.jsonl", "learning-ledger.jsonl"],
                "completed_artifacts": ["daily-analytics.jsonl"],
                "learning_recorded": False,
                "learning_status": None,
                "experiment_outcome": None,
                "next_measurement_trigger": None,
            }
        )
    ledger["stages"] = stages
    atomic_write_json(ledger_path, ledger)
    runtime_reconciliation = None
    if state_path.is_file():
        state = load_object(state_path)
        queue = load_object(queue_path)
        ledger = load_object(ledger_path)
        runtime_reconciliation = reconcile_runtime(
            state_dir,
            state,
            config,
            queue,
            ledger,
            current_time(args.now),
            startup=False,
        )
        atomic_write_json(state_path, state)
        atomic_write_json(queue_path, queue)
        atomic_write_json(ledger_path, ledger)
    for directory in (state_dir / "brand" / "watermarks", state_dir / "gif-reference-captures"):
        if not directory.exists():
            directory.mkdir(parents=True)
            created.append(str(directory.relative_to(state_dir)) + "/")

    print(
        json.dumps(
            {
                "migrated": str(state_dir),
                "config_updated": changed,
                "state_updated": state_updated,
                "consent_updated": consent_updated,
                "created": created,
                "runtime_reconciliation": runtime_reconciliation,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
