#!/usr/bin/env python3
"""Validate the minimum campaign configuration, consent, and state invariants."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REQUIRED_FILES = ("campaign-config.json", "consent-record.json", "campaign-state.json")
REQUIRED_ARTIFACTS = (
    "work-queue.json",
    "stage-ledger.json",
    "working-algorithm-model.json",
    "signal-events.jsonl",
    "schedule-decisions.jsonl",
    "publication-evidence.jsonl",
    "task-events.jsonl",
    "recovery-events.jsonl",
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

    ids = {doc.get("campaign_id") for doc in docs.values() if doc}
    if not ids or None in ids or "replace-me" in ids:
        errors.append("campaign_id must be set in all required files")
    elif len(ids) != 1:
        errors.append(f"campaign_id mismatch: {sorted(ids)}")

    target = config.get("target", {})
    for key in ("name", "completion_formula", "required_evidence"):
        if target.get(key) in (None, "", []):
            errors.append(f"campaign-config.json target.{key} must be set")
    expected_metrics = {"metric_a": "followers", "metric_b": "connections"}
    for metric_key, expected_name in expected_metrics.items():
        metric = target.get(metric_key, {})
        if metric.get("name") != expected_name:
            errors.append(
                f"campaign-config.json target.{metric_key}.name must equal {expected_name}"
            )
        if isinstance(metric.get("baseline"), (int, float)) and metric["baseline"] < 0:
            errors.append(f"campaign-config.json target.{metric_key}.baseline must not be negative")
        if metric.get("goal") != 10000:
            errors.append(f"campaign-config.json target.{metric_key}.goal must equal 10000")

    owner = consent.get("owner", {})
    if owner.get("display_name") != "Sunny Chandel":
        errors.append("consent-record.json owner.display_name must equal Sunny Chandel")
    if owner.get("expected_linkedin_identity") != "Sunny Chandel":
        errors.append("consent-record.json owner.expected_linkedin_identity must equal Sunny Chandel")
    if consent.get("status") != "active" and not args.allow_draft:
        errors.append("consent-record.json status must be active")
    if consent.get("consent_version") != "2.0":
        errors.append("consent-record.json consent_version must equal 2.0")
    if consent.get("scope") != "campaign-lifetime":
        errors.append("consent-record.json scope must equal campaign-lifetime")
    if not consent.get("activated_at") and not args.allow_draft:
        errors.append("consent-record.json activated_at must be set")
    receipt = consent.get("authorization_receipt", {})
    if not args.allow_draft and (
        not isinstance(receipt, dict)
        or not receipt.get("receipt_id")
        or not receipt.get("granted_at")
        or receipt.get("portable_across_model_sessions") is not True
    ):
        errors.append("consent-record.json must contain a persistent authorization receipt")
    reconfirmation = consent.get("reconfirmation_policy", {})
    if reconfirmation.get("routine_reconfirmation_required") is not False:
        errors.append("consent-record.json routine reconfirmation must be disabled")
    accounts = consent.get("accounts", [])
    expected_url = "https://www.linkedin.com/in/sunny-chandel-6a05bb401/"
    if not any(account.get("url") == expected_url for account in accounts if isinstance(account, dict)):
        errors.append("consent-record.json accounts must contain Sunny's fixed LinkedIn profile URL")
    if not consent.get("approved_action_classes"):
        errors.append("consent-record.json approved_action_classes must be set")
    if not consent.get("data_directory"):
        errors.append("consent-record.json data_directory must be set")
    persistent_settings = consent.get("persistent_settings", [])
    required_settings = {
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
    }
    if not isinstance(persistent_settings, list) or not required_settings.issubset(set(persistent_settings)):
        errors.append("consent-record.json persistent_settings must contain the active automation envelope")
    lifecycle = state.get("lifecycle_state")
    if lifecycle not in VALID_STATES:
        errors.append(f"campaign-state.json lifecycle_state must be one of {sorted(VALID_STATES)}")
    if config.get("schema_version") != "1.2":
        errors.append("campaign-config.json schema_version must equal 1.2")
    if state.get("schema_version") != "1.2":
        errors.append("campaign-state.json schema_version must equal 1.2")

    fixed = config.get("fixed_rules", {})
    expected = {
        "posts_per_day": 2,
        "prepared_packages_per_content_day": 2,
        "max_actions_per_burst": 10,
        "base_actions_per_day": 100,
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
    if not isinstance(dispatch.get("priority_order"), list) or len(dispatch["priority_order"]) != 8:
        errors.append("campaign-config.json adaptive_dispatch.priority_order must contain eight priorities")

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
    if browser_rules.get("routine_device_questions_allowed") is not False:
        errors.append("automation_reliability.browser_binding.routine_device_questions_allowed must equal false")
    circuit_rules = reliability.get("circuit_breaker", {})
    if circuit_rules.get("max_safe_retries") != 2 or circuit_rules.get("continue_offline_lane") is not True:
        errors.append("automation_reliability.circuit_breaker is invalid")
    reserve_rules = reliability.get("reserve", {})
    if reserve_rules.get("max_pages_per_pass") != 5 or reserve_rules.get("max_minutes_per_pass") != 8:
        errors.append("automation_reliability.reserve pass limits are invalid")

    publishing_config = config.get("publishing_optimization", {})
    publishing_expected = {
        "mode": "fully-dynamic",
        "required_regions": ["india", "us-central"],
        "fixed_publish_times": [],
        "fixed_spacing_minutes": None,
        "dynamic_cannibalization_penalty": True,
        "no_extra_stockpile": True,
    }
    for key, value in publishing_expected.items():
        if publishing_config.get(key) != value:
            errors.append(f"campaign-config.json publishing_optimization.{key} must equal {value}")

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
    if scaling.get("base_daily_ceiling") != 100:
        errors.append("campaign-state.json engagement_scaling.base_daily_ceiling must equal 100")
    budget_day = scaling.get("budget_day_ist")
    if budget_day is not None and (not isinstance(budget_day, str) or len(budget_day) != 10):
        errors.append("campaign-state.json engagement_scaling.budget_day_ist must be an IST date or null")
    base_used = scaling.get("base_actions_used")
    if isinstance(base_used, bool) or not isinstance(base_used, int) or not 0 <= base_used <= 100:
        errors.append("campaign-state.json engagement_scaling.base_actions_used must be from 0 to 100")
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
    if browser_binding.get("selection_policy") != "reuse-pinned-device-without-question":
        errors.append("campaign-state.json browser binding selection policy is invalid")
    automation_consent = state.get("automation_consent", {})
    if not args.allow_draft and (
        automation_consent.get("status") != "active"
        or automation_consent.get("reconfirmation_required") is not False
        or not automation_consent.get("receipt_id")
    ):
        errors.append("campaign-state.json must contain a loaded active consent snapshot")
    publishing_state = state.get("publishing", {})
    for key in ("packages_ready", "posts_published"):
        value = publishing_state.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 2:
            errors.append(f"campaign-state.json publishing.{key} must be from 0 to 2")

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
    }
    if algorithm and not required_models.issubset(set(algorithm.get("scheduling_models", {}))):
        errors.append("working-algorithm-model.json scheduling_models is incomplete")

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
