#!/usr/bin/env python3
"""Validate the minimum campaign configuration, consent, and state invariants."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


REQUIRED_FILES = ("campaign-config.json", "consent-record.json", "campaign-state.json")
REQUIRED_ARTIFACTS = (
    "external-executor.json",
    "work-queue.json",
    "stage-ledger.json",
    "working-algorithm-model.json",
    "signal-events.jsonl",
    "schedule-decisions.jsonl",
    "publication-evidence.jsonl",
    "task-events.jsonl",
    "recovery-events.jsonl",
    "engagement-opportunities.json",
    "opportunity-health.jsonl",
    "operational-output.json",
    "content-pipeline.json",
    "regional-performance.json",
    "repair-state.json",
    "repair-events.jsonl",
    "external-executor-events.jsonl",
)
VALID_STATES = {"ready", "running", "recovering", "hard-blocked", "completed", "user-stopped"}


def load_json(path: Path, errors: list[str]) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"missing file: {path.name}")
        return {}
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON in {path.name}: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{path.name} must contain a JSON object")
        return {}
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state_dir", type=Path)
    parser.add_argument("--allow-draft", action="store_true", help="validate structure before activation")
    args = parser.parse_args()

    state_dir = args.state_dir.expanduser().resolve()
    errors: list[str] = []
    docs = {name: load_json(state_dir / name, errors) for name in REQUIRED_FILES}
    config = docs["campaign-config.json"]
    consent = docs["consent-record.json"]
    state = docs["campaign-state.json"]
    for name in REQUIRED_ARTIFACTS:
        if not (state_dir / name).is_file():
            errors.append(f"missing file: {name}")
    executor = load_json(state_dir / "external-executor.json", errors)
    if executor:
        if executor.get("unattended") is not True:
            errors.append("external-executor.json unattended must equal true")
        if executor.get("interactive_fallback_enabled") is not False:
            errors.append(
                "external-executor.json interactive_fallback_enabled must equal false"
            )
        if executor.get("status") not in {"unconfigured", "active", "blocked", "disabled"}:
            errors.append("external-executor.json status is invalid")
        credential_source = executor.get("credential_source", {})
        if not isinstance(credential_source, dict) or credential_source.get("type") not in {
            "environment", "environment-or-macos-keychain"
        }:
            errors.append("external-executor.json credential_source type is invalid")
        token_refresh = executor.get("token_refresh", {})
        if not isinstance(token_refresh, dict) or token_refresh.get("mode") != "programmatic":
            errors.append("external-executor.json must require programmatic token refresh")

    ids = {doc.get("campaign_id") for doc in docs.values() if doc}
    if not ids or None in ids or "replace-me" in ids:
        errors.append("campaign_id must be set in all required files")
    elif len(ids) != 1:
        errors.append(f"campaign_id mismatch: {sorted(ids)}")

    target = config.get("target", {})
    for key in ("name", "completion_formula", "required_evidence"):
        if target.get(key) in (None, "", []):
            errors.append(f"campaign-config.json target.{key} must be set")
    expected_metrics = {"metric_a": {"followers"}, "metric_b": {"connections", "impressions"}}
    for metric_key, expected_names in expected_metrics.items():
        metric = target.get(metric_key, {})
        if metric.get("name") not in expected_names:
            errors.append(
                f"campaign-config.json target.{metric_key}.name must be one of {sorted(expected_names)}"
            )
        if isinstance(metric.get("baseline"), (int, float)) and metric["baseline"] < 0:
            errors.append(f"campaign-config.json target.{metric_key}.baseline must not be negative")
        goal = metric.get("goal")
        if isinstance(goal, bool) or not isinstance(goal, (int, float)) or goal <= 0:
            errors.append(f"campaign-config.json target.{metric_key}.goal must be positive")
    if target.get("metric_a", {}).get("goal_mode") not in {None, "absolute", "increase"}:
        errors.append("campaign-config.json target.metric_a.goal_mode is invalid")
    metric_b = target.get("metric_b", {})
    if metric_b.get("name") == "impressions" and metric_b.get("goal_mode") != "window-total":
        errors.append("campaign-config.json impressions target must use window-total goal mode")
    duration_days = target.get("duration_days")
    if duration_days is not None and (
        isinstance(duration_days, bool) or not isinstance(duration_days, int) or duration_days <= 0
    ):
        errors.append("campaign-config.json target.duration_days must be a positive integer")

    owner = consent.get("owner", {})
    display_name = owner.get("display_name")
    expected_identity = owner.get("expected_linkedin_identity")
    if not isinstance(display_name, str) or not display_name.strip() or display_name == "replace-me":
        errors.append("consent-record.json owner.display_name must identify the profile owner")
    if expected_identity != display_name:
        errors.append("consent-record.json owner.expected_linkedin_identity must match owner.display_name")
    if consent.get("status") != "active" and not args.allow_draft:
        errors.append("consent-record.json status must be active")
    if consent.get("consent_version") != "2.0":
        errors.append("consent-record.json consent_version must equal 2.0")
    if consent.get("scope") != "campaign-lifetime":
        errors.append("consent-record.json scope must equal campaign-lifetime")
    if not consent.get("activated_at") and not args.allow_draft:
        errors.append("consent-record.json activated_at must be set")
    receipt = consent.get("operating_receipt", {})
    if not args.allow_draft and (
        not isinstance(receipt, dict)
        or not receipt.get("receipt_id")
        or not receipt.get("granted_at")
        or receipt.get("portable_across_model_sessions") is not True
    ):
        errors.append("consent-record.json must contain a persistent operating receipt")
    renewal = consent.get("renewal_policy", {})
    if renewal.get("routine_renewal_required") is not False:
        errors.append("consent-record.json routine renewal must be disabled")
    accounts = consent.get("accounts", [])
    linkedin_accounts = [
        account
        for account in accounts
        if isinstance(account, dict) and account.get("type") == "linkedin-profile"
    ]
    if len(linkedin_accounts) != 1:
        errors.append("consent-record.json accounts must contain exactly one LinkedIn profile")
    elif not str(linkedin_accounts[0].get("url", "")).startswith("https://www.linkedin.com/in/"):
        errors.append("consent-record.json LinkedIn account must use a full profile URL")
    elif linkedin_accounts[0].get("owner") != display_name:
        errors.append("consent-record.json LinkedIn account owner must match owner.display_name")
    if not consent.get("configured_action_classes"):
        errors.append("consent-record.json configured_action_classes must be set")
    if not consent.get("data_directory"):
        errors.append("consent-record.json data_directory must be set")
    configured_timezone = config.get("timezone")
    try:
        if not isinstance(configured_timezone, str) or not configured_timezone:
            raise ZoneInfoNotFoundError
        ZoneInfo(configured_timezone)
    except ZoneInfoNotFoundError:
        errors.append("campaign-config.json timezone must be a valid IANA timezone")
    persistent_settings = consent.get("persistent_settings", [])
    required_settings = {
        "automatic-local-workspace",
        "continuous-local-dispatch",
        "evidence-based-scheduling",
        "automatic-profile-watermark",
        "creative-pattern-learning",
        "campaign-start-operating-receipt",
        "campaign-lifetime-receipt-reload",
        "automatic-recovery-and-continuation",
        "opportunity-recovery-controller",
        "six-package-ready-inventory",
        "regional-diversification",
        "automatic-runtime-repair",
    }
    if not isinstance(persistent_settings, list) or not required_settings.issubset(set(persistent_settings)):
        errors.append("consent-record.json persistent_settings must contain the active automation envelope")
    lifecycle = state.get("lifecycle_state")
    if lifecycle not in VALID_STATES:
        errors.append(f"campaign-state.json lifecycle_state must be one of {sorted(VALID_STATES)}")
    if config.get("schema_version") != "2.0":
        errors.append("campaign-config.json schema_version must equal 2.0")
    if state.get("schema_version") != "2.0":
        errors.append("campaign-state.json schema_version must equal 2.0")

    fixed = config.get("fixed_rules", {})
    expected = {
        "minimum_posts_rolling_24h": 6,
        "maximum_posts_rolling_24h": 8,
        "rolling_package_inventory": 6,
        "topic_candidates_per_portfolio": 12,
        "max_actions_per_burst": 10,
        "rolling_24h_action_target": 160,
        "rolling_24h_action_cap": 200,
        "direct_reply_overage_allowed": True,
        "new_target_min_followers": 3000,
        "cooldown_hours": 72,
        "max_proactive_actions_per_person_per_7d": 2,
    }
    for key, value in expected.items():
        if fixed.get(key) != value:
            errors.append(f"campaign-config.json fixed_rules.{key} must equal {value}")

    engagement = config.get("engagement_optimization", {})
    if engagement.get("adaptive_fill") is not True:
        errors.append("campaign-config.json engagement_optimization.adaptive_fill must equal true")
    if engagement.get("minimum_action_score") != 65:
        errors.append("campaign-config.json engagement_optimization.minimum_action_score must equal 65")
    engagement_weights = engagement.get("weights", {})
    expected_engagement_keys = {
        "qualified_growth",
        "audience_spillover",
        "conversation_probability",
        "target_relevance",
        "freshness_timing",
        "historical_performance",
    }
    if set(engagement_weights) != expected_engagement_keys:
        errors.append("campaign-config.json engagement_optimization.weights has invalid keys")
    elif any(isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1 for value in engagement_weights.values()):
        errors.append("campaign-config.json engagement_optimization.weights values must be from 0 to 1")
    elif abs(sum(engagement_weights.values()) - 1.0) > 1e-9:
        errors.append("campaign-config.json engagement_optimization.weights must sum to 1.0")
    if "clusters" in engagement:
        errors.append("campaign-config.json engagement_optimization.clusters must be removed")

    dispatch = config.get("adaptive_dispatch", {})
    dispatch_expected = {
        "enabled": True,
        "operating_span": "24h",
        "burst_gap_mode": "fully-adaptive",
        "wait_requires_empty_validated_queue": True,
        "reserve_mode": "adaptive-next-two-bursts",
    }
    for key, value in dispatch_expected.items():
        if dispatch.get(key) != value:
            errors.append(f"campaign-config.json adaptive_dispatch.{key} must equal {value}")
    required_task_priorities = {
        "opportunity-discovery",
        "engagement-burst-execution",
        "rolling-output-evaluation",
        "regional-allocation",
        "six-package-replenishment",
        "publication-execution",
        "scheduled-analytics-snapshot",
        "publishing-debt-recovery",
        "runtime-repair",
    }
    if not isinstance(dispatch.get("priority_order"), list) or not required_task_priorities.issubset(set(dispatch["priority_order"])):
        errors.append("campaign-config.json adaptive_dispatch.priority_order is missing recovery task priorities")

    recovery = config.get("opportunity_recovery", {})
    expected_health_weights = {
        "equal_age_impressions": 0.25,
        "engagement_rate": 0.2,
        "profile_view_velocity": 0.2,
        "follower_connection_growth": 0.1,
        "action_pace": 0.15,
        "reserve_coverage_yield": 0.1,
    }
    if recovery.get("health_weights") != expected_health_weights:
        errors.append("campaign-config.json opportunity_recovery.health_weights is invalid")
    if recovery.get("activation_threshold") != 70 or recovery.get("exit_threshold") != 80:
        errors.append("campaign-config.json opportunity recovery thresholds are invalid")
    expected_tiers = {
        "normal": {"minimum_score": 65, "new_target_min_followers": 3000, "cooldown_hours": 72},
        "expansion": {"minimum_score": 60, "new_target_min_followers": 2000, "cooldown_hours": 48},
        "intensive": {"minimum_score": 55, "new_target_min_followers": 1000, "cooldown_hours": 24},
    }
    if recovery.get("tiers") != expected_tiers:
        errors.append("campaign-config.json opportunity_recovery.tiers is invalid")
    if len(recovery.get("source_rotation", [])) != 8:
        errors.append("campaign-config.json opportunity_recovery.source_rotation must contain eight sources")
    expected_milestones = [
        {"day_fraction": 0.25, "actions": 40},
        {"day_fraction": 0.5, "actions": 80},
        {"day_fraction": 0.75, "actions": 120},
        {"day_fraction": 1.0, "actions": 160},
    ]
    if recovery.get("daily_action_milestones") != expected_milestones:
        errors.append("campaign-config.json opportunity recovery milestones must be 40/80/120/160")

    reliability = config.get("automation_reliability", {})
    reliability_expected = {
        "consent_mode": "single-owner-grant",
        "consent_persistence": "campaign-lifetime",
        "task_lease_minutes": 15,
        "max_consecutive_same_task_type": 2,
        "preflight_evidence_ttl_minutes": 30,
    }
    for key, value in reliability_expected.items():
        if reliability.get(key) != value:
            errors.append(f"campaign-config.json automation_reliability.{key} must equal {value}")
    browser_rules = reliability.get("browser_binding", {})
    if browser_rules.get("reuse_pinned_device") is not True:
        errors.append("automation_reliability.browser_binding.reuse_pinned_device must equal true")
    if browser_rules.get("direct_pinned_device_selection") is not True:
        errors.append("automation_reliability.browser_binding.direct_pinned_device_selection must equal true")
    circuit_rules = reliability.get("circuit_breaker", {})
    if circuit_rules.get("max_safe_retries") != 2 or circuit_rules.get("continue_offline_lane") is not True:
        errors.append("automation_reliability.circuit_breaker is invalid")
    reserve_rules = reliability.get("reserve", {})
    if reserve_rules.get("max_pages_per_pass") != 5 or reserve_rules.get("max_minutes_per_pass") != 8:
        errors.append("automation_reliability.reserve pass limits are invalid")
    if reserve_rules.get("min_target") != 40 or int(reserve_rules.get("max_target", 0) or 0) < 40:
        errors.append("automation_reliability.reserve must maintain at least 40 opportunities")

    publishing_config = config.get("publishing_optimization", {})
    publishing_expected = {
        "mode": "fully-dynamic",
        "required_regions": ["india", "india", "us", "us", "uk-eu", "apac"],
        "fixed_publish_times": [],
        "fixed_spacing_minutes": None,
        "dynamic_cannibalization_penalty": True,
        "minimum_posts_rolling_24h": 6,
        "maximum_posts_rolling_24h": 8,
        "rolling_inventory_target": 6,
        "normal_publications": 6,
        "maximum_recovery_publications": 2,
        "minimum_recovery_spacing_minutes": 120,
        "maximum_unpublished_recovery_packages": 1,
        "minimum_content_pillars_per_portfolio": 4,
        "minimum_format_treatments_per_portfolio": 3,
        "normal_inventory_replenishment": "one-after-each-publication",
        "no_consecutive_topic_angle_or_format": True,
    }
    for key, value in publishing_expected.items():
        if publishing_config.get(key) != value:
            errors.append(f"campaign-config.json publishing_optimization.{key} must equal {value}")
    priority_window = publishing_config.get("production_priority_window", {})
    if priority_window.get("timezone") != configured_timezone:
        errors.append("publishing production window timezone must match campaign timezone")
    regional_config = config.get("regional_intelligence", {})
    if regional_config.get("bootstrap_allocation") != ["india", "india", "us", "us", "uk-eu", "apac"]:
        errors.append("regional_intelligence.bootstrap_allocation is invalid")
    if regional_config.get("required_minimums") != {"india": 1, "us": 1}:
        errors.append("regional_intelligence must retain India and US minimums")
    if config.get("analytics_contract", {}).get("checkpoints_minutes") != [30, 120, 360, 1440]:
        errors.append("analytics checkpoints must be 30, 120, 360, and 1440 minutes")
    repair_config = config.get("runtime_repair", {})
    if repair_config.get("enabled") is not True or repair_config.get("continue_unaffected_work") is not True:
        errors.append("runtime_repair must be enabled and continue unaffected work")

    brand = config.get("brand_system", {})
    brand_expected = {
        "auto_create": True,
        "auto_apply": True,
        "watermark_height_ratio": 0.06,
        "watermark_opacity": 0.85,
        "safe_area_inset_ratio": 0.04,
    }
    for key, value in brand_expected.items():
        if brand.get(key) != value:
            errors.append(f"campaign-config.json brand_system.{key} must equal {value}")

    gif = config.get("gif_creative_intelligence", {})
    gif_expected = {
        "enabled": True,
        "formats": ["gif"],
        "core_creator_count": 12,
        "rotating_creator_count": 8,
        "references_per_creator": 2,
        "dominant_score": 85,
        "dominant_margin": 15,
        "permanent_deletion": True,
    }
    for key, value in gif_expected.items():
        if gif.get(key) != value:
            errors.append(f"campaign-config.json gif_creative_intelligence.{key} must equal {value}")

    scaling = state.get("engagement_scaling", {})
    if scaling.get("rolling_action_target") != 160 or scaling.get("rolling_action_cap") != 200:
        errors.append("campaign-state.json rolling action contract must equal 160 target and 200 cap")
    base_used = scaling.get("rolling_24h_actions")
    if isinstance(base_used, bool) or not isinstance(base_used, int) or not 0 <= base_used <= 200:
        errors.append("campaign-state.json engagement_scaling.rolling_24h_actions must be from 0 to 200")
    overage = scaling.get("direct_reply_overage")
    if isinstance(overage, bool) or not isinstance(overage, int) or overage < 0:
        errors.append("campaign-state.json engagement_scaling.direct_reply_overage must be non-negative")
    if not isinstance(scaling.get("burst_history"), list):
        errors.append("campaign-state.json engagement_scaling.burst_history must be an array")

    dispatcher = state.get("dispatcher", {})
    for lane in ("linkedin_lane", "offline_lane"):
        if dispatcher.get(lane) not in {"ready", "recovering", "blocked"}:
            errors.append(f"campaign-state.json dispatcher.{lane} is invalid")
    browser_binding = dispatcher.get("browser_binding", {})
    if browser_binding.get("selection_policy") != "reuse-pinned-device-directly":
        errors.append("campaign-state.json browser binding selection policy is invalid")
    continuation = dispatcher.get("continuation", {})
    if continuation.get("schedule_kind") != "recurring-cron":
        errors.append("campaign-state.json continuation must use a recurring cron schedule")
    if continuation.get("recurrence_cron") != "0 * * * *":
        errors.append("campaign-state.json continuation recurring cron must run hourly")
    if continuation.get("expiry_policy") != "stable-recurring-until-target-or-stop-signal":
        errors.append("campaign-state.json continuation must remain recurring until completion or stop")
    if continuation.get("renew_existing_automation") is not False:
        errors.append("campaign-state.json continuation must not renew the recurring routine per wait")
    if continuation.get("renewal_due_before_expiry") is not False:
        errors.append("campaign-state.json recurring continuation must not require expiry renewal")
    if continuation.get("update_schedule_for_next_wake") is not False:
        errors.append("campaign-state.json recurring continuation must keep its schedule unchanged")
    automation_consent = state.get("automation_consent", {})
    if not args.allow_draft and (
        automation_consent.get("status") != "active"
        or automation_consent.get("renewal_required") is not False
        or not automation_consent.get("receipt_id")
    ):
        errors.append("campaign-state.json must contain a loaded active consent snapshot")
    publishing_state = state.get("publishing", {})
    for key in ("packages_ready",):
        value = publishing_state.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 6:
            errors.append(f"campaign-state.json publishing.{key} must be from 0 to 6")
    posts_published = publishing_state.get("rolling_24h_posts")
    if isinstance(posts_published, bool) or not isinstance(posts_published, int) or not 0 <= posts_published <= 8:
        errors.append("campaign-state.json publishing.rolling_24h_posts must be from 0 to 8")

    opportunities = load_json(state_dir / "engagement-opportunities.json", errors)
    if opportunities and not isinstance(opportunities.get("opportunities"), list):
        errors.append("engagement-opportunities.json opportunities must be an array")

    work_queue = load_json(state_dir / "work-queue.json", errors)
    if work_queue and not isinstance(work_queue.get("items"), list):
        errors.append("work-queue.json items must be an array")
    elif work_queue:
        allowed_task_statuses = {
            "pending",
            "recovering",
            "missed-recovering",
            "retry-wait",
            "leased",
            "running",
            "completed",
            "blocked",
            "superseded",
            "expired",
            "cancelled",
        }
        for position, item in enumerate(work_queue.get("items", [])):
            if not isinstance(item, dict):
                errors.append(f"work-queue.json items[{position}] must be an object")
                continue
            if item.get("status") not in allowed_task_statuses:
                errors.append(f"work-queue.json items[{position}].status is invalid")
            if item.get("status") in {"leased", "running"} and not item.get("lease_expires_at"):
                errors.append(f"work-queue.json items[{position}] active lease must expire")
    stage_ledger = load_json(state_dir / "stage-ledger.json", errors)
    if stage_ledger and not isinstance(stage_ledger.get("stages"), list):
        errors.append("stage-ledger.json stages must be an array")
    algorithm = load_json(state_dir / "working-algorithm-model.json", errors)
    required_models = {
        "publication_timing",
        "response_latency",
        "regional_opportunity",
        "concentration",
        "candidate_staleness",
        "source_yield",
        "gate_tier",
        "action_type",
        "recovery_post",
        "action_to_profile_view",
        "follower_conversion",
        "format_performance",
        "topic_performance",
        "regional_spillover",
    }
    if algorithm and not required_models.issubset(set(algorithm.get("scheduling_models", {}))):
        errors.append("working-algorithm-model.json scheduling_models is incomplete")

    operational = load_json(state_dir / "operational-output.json", errors)
    if operational:
        actions = operational.get("actions", {})
        publishing_output = operational.get("publishing", {})
        if actions.get("target") != 160 or actions.get("hard_cap") != 200:
            errors.append("operational-output.json action contract must be 160/200")
        if publishing_output.get("target") != 6 or publishing_output.get("hard_cap") != 8:
            errors.append("operational-output.json publishing contract must be 6/8")
    pipeline = load_json(state_dir / "content-pipeline.json", errors)
    if pipeline and not all(isinstance(pipeline.get(key), list) for key in ("topic_candidates", "briefs", "packages")):
        errors.append("content-pipeline.json topic_candidates, briefs, and packages must be arrays")
    regional = load_json(state_dir / "regional-performance.json", errors)
    if regional and not isinstance(regional.get("observations"), list):
        errors.append("regional-performance.json observations must be an array")
    repair = load_json(state_dir / "repair-state.json", errors)
    if repair and repair.get("status") not in {"healthy", "repair-pending", "verification-pending", "recovering"}:
        errors.append("repair-state.json status is invalid")

    subscription = config.get("subscription_optimization", {})
    if subscription.get("enabled") is not True:
        errors.append("campaign-config.json subscription_optimization.enabled must equal true")
    for key in (
        "purchases_allowed",
        "paid_plan_upgrades_allowed",
        "billing_changes_allowed",
        "paid_trial_starts_allowed",
    ):
        if subscription.get(key) is not False:
            errors.append(f"campaign-config.json subscription_optimization.{key} must equal false")
    weights = subscription.get("weights", {})
    expected_weight_keys = {
        "campaign_relevance",
        "unused_capacity",
        "evidence_strength",
        "expiry_urgency",
        "implementation_readiness",
    }
    if set(weights) != expected_weight_keys:
        errors.append("campaign-config.json subscription_optimization.weights has invalid keys")
    elif any(isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1 for value in weights.values()):
        errors.append("campaign-config.json subscription_optimization.weights values must be from 0 to 1")
    elif abs(sum(weights.values()) - 1.0) > 1e-9:
        errors.append("campaign-config.json subscription_optimization.weights must sum to 1.0")

    result = {"valid": not errors, "state_dir": str(state_dir), "errors": errors}
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
