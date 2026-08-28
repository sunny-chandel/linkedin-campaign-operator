#!/usr/bin/env python3
"""Add current safe defaults and artifacts to an existing campaign directory."""

from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from runtime_state import current_time, reconcile_runtime
from package_version import CURRENT_VERSION


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


def import_legacy_opportunities(state_dir: Path, campaign_id: str, now: datetime) -> int:
    """Import evidence-backed legacy candidates without reviving stale/executed work."""
    path = state_dir / "engagement-opportunities.json"
    document = load_object(path)
    opportunities = document.setdefault("opportunities", [])
    existing = {
        str(item.get("candidate_id")): item
        for item in opportunities
        if isinstance(item, dict) and item.get("candidate_id")
    }
    interaction_text = (
        (state_dir / "interaction-log.jsonl").read_text(encoding="utf-8")
        if (state_dir / "interaction-log.jsonl").is_file()
        else ""
    )
    imported = 0
    weights = {
        "qualified_growth": 0.35,
        "audience_spillover": 0.20,
        "conversation_probability": 0.15,
        "target_relevance": 0.15,
        "freshness_timing": 0.10,
        "historical_performance": 0.05,
    }
    for legacy_path in sorted((state_dir / "logs").glob("adaptive-reserve-candidates*.json")):
        try:
            legacy = load_object(legacy_path)
        except (OSError, json.JSONDecodeError, ValueError):
            continue
        observed_raw = legacy.get("identification_pass_at")
        observed = None
        if isinstance(observed_raw, str):
            try:
                observed = datetime.fromisoformat(observed_raw.replace("Z", "+00:00"))
                if observed.tzinfo is None:
                    observed = observed.replace(tzinfo=timezone.utc)
                observed = observed.astimezone(timezone.utc)
            except ValueError:
                observed = None
        for candidate in legacy.get("candidates", []):
            if not isinstance(candidate, dict) or not candidate.get("candidate_id"):
                continue
            candidate_id = str(candidate["candidate_id"])
            if candidate_id in existing:
                continue
            evidence_complete = bool(
                candidate.get("qualified") is True
                and candidate.get("action_available") is True
                and candidate.get("cooldown_passed") is True
                and candidate.get("profile_url")
                and all(isinstance(candidate.get(key), (int, float)) for key in weights)
            )
            stale = observed is None or (now - observed).total_seconds() > 86400
            profile_url = str(candidate.get("profile_url") or "")
            executed = candidate_id in interaction_text or bool(profile_url and profile_url in interaction_text)
            status = "executed" if executed else "stale" if stale else "qualified" if evidence_complete else "needs-revalidation"
            score = round(sum(float(candidate.get(key, 0)) * weight for key, weight in weights.items()) * 100, 2)
            normalized = {
                "candidate_id": candidate_id,
                "candidate_identity": candidate.get("profile_url") or candidate_id,
                "name": candidate.get("name"),
                "profile_url": candidate.get("profile_url"),
                "source": candidate.get("source") or "legacy-adaptive-reserve",
                "lane": candidate.get("lane", "proactive"),
                "score": score,
                "active_gate_tier": "normal",
                "post_freshness": candidate.get("post_reference"),
                "cooldown_passed": candidate.get("cooldown_passed") is True,
                "follower_count": candidate.get("followers"),
                "target_status": candidate.get("target_list_status", "new"),
                "action_type": candidate.get("action_type", "comment"),
                "action_available": candidate.get("action_available") is True,
                "proactive_actions_person_7d": candidate.get("proactive_interactions_7d", 0),
                "status": status,
                "lifecycle_status": status,
                "discovered_at": observed.isoformat() if observed else None,
                "expires_at": (
                    (observed + timedelta(hours=24)).isoformat()
                    if observed else None
                ),
                "evidence": {
                    "legacy_file": str(legacy_path.relative_to(state_dir)),
                    "rationale": candidate.get("rationale"),
                    "post_reference": candidate.get("post_reference"),
                    "excluded_reason": candidate.get("excluded_reason"),
                },
            }
            opportunities.append(normalized)
            existing[candidate_id] = normalized
            imported += 1
    document["schema_version"] = "2.0"
    document["campaign_id"] = campaign_id
    document["updated_at"] = now.isoformat()
    atomic_write_json(path, document)
    return imported


def import_legacy_packages(state_dir: Path, campaign_id: str, now: datetime) -> int:
    """Place legacy package evidence into the v6 pipeline without inventing validation."""
    path = state_dir / "content-pipeline.json"
    pipeline = load_object(path)
    packages = pipeline.setdefault("packages", [])
    existing = {
        str(item.get("package_id")) for item in packages
        if isinstance(item, dict) and item.get("package_id")
    }
    publication_text = (
        (state_dir / "publication-evidence.jsonl").read_text(encoding="utf-8")
        if (state_dir / "publication-evidence.jsonl").is_file() else ""
    )
    imported = 0
    for package_path in sorted(state_dir.glob("**/publication-package*.json")):
        if package_path == path:
            continue
        try:
            value = load_object(package_path)
        except (OSError, json.JSONDecodeError, ValueError):
            continue
        package_id = str(value.get("package_id") or value.get("post_id") or package_path.stem)
        if package_id in existing:
            continue
        expiry = value.get("freshness_expiry")
        expiry_time = None
        if isinstance(expiry, str):
            try:
                expiry_time = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
                if expiry_time.tzinfo is None:
                    expiry_time = expiry_time.replace(tzinfo=timezone.utc)
                expiry_time = expiry_time.astimezone(timezone.utc)
            except ValueError:
                expiry_time = None
        published = package_id in publication_text or str(value.get("post_url") or "") in publication_text
        legacy_ready = str(
            value.get("final_validation_status") or value.get("validation_status") or ""
        ).startswith("ready")
        required_fields = {
            "region": value.get("target_region") or value.get("region"),
            "demographic_hypothesis": value.get("demographic_hypothesis"),
            "freshness_expiry": expiry,
            "portfolio_role": value.get("portfolio_role"),
            "competing_angle": value.get("competing_angle"),
            "intended_growth_outcome": value.get("intended_growth_outcome"),
        }
        complete = legacy_ready and all(required_fields.values()) and bool(
            value.get("content_pillar") and (value.get("format_treatment") or value.get("format"))
        )
        status = (
            "published" if published else
            "stale-replacement-required" if expiry_time is not None and expiry_time <= now else
            "validated" if complete else
            "needs-v6-revalidation"
        )
        packages.append({
            "package_id": package_id,
            "status": status,
            "source_path": str(package_path.relative_to(state_dir)),
            "region": required_fields["region"],
            "demographic_hypothesis": required_fields["demographic_hypothesis"],
            "freshness_expiry": expiry,
            "portfolio_role": required_fields["portfolio_role"],
            "competing_angle": required_fields["competing_angle"],
            "intended_growth_outcome": required_fields["intended_growth_outcome"],
            "topic": value.get("topic"),
            "angle": value.get("angle"),
            "content_pillar": value.get("content_pillar"),
            "format_treatment": value.get("format_treatment") or value.get("format"),
            "replacement_required": status == "stale-replacement-required",
            "analytics_contract": "legacy-preserved" if published else "v6-four-checkpoints",
            "stages": {
                "research_brief": bool(value.get("research_brief") or value.get("research_brief_path")),
                "claim_verification": bool(value.get("claim_verification") or value.get("claims_verified")),
                "caption": bool(value.get("caption") or value.get("caption_path")),
                "asset": bool(value.get("asset") or value.get("asset_path")),
                "watermark": bool(value.get("watermark") or value.get("watermark_applied")),
                "validation": legacy_ready,
                "publication_decision": bool(value.get("publication_decision")),
                "live_verification": published,
            },
            "migration_evidence": "legacy-package-file",
        })
        existing.add(package_id)
        imported += 1
    ready_count = sum(
        1 for item in packages
        if isinstance(item, dict) and item.get("status") in {"ready", "validated"}
    )
    pipeline["schema_version"] = "2.0"
    pipeline["campaign_id"] = campaign_id
    pipeline["inventory"] = {
        "target": 6,
        "validated_unpublished": ready_count,
        "debt": max(0, 6 - ready_count),
        "evaluated_at": now.isoformat(),
    }
    pipeline["updated_at"] = now.isoformat()
    atomic_write_json(path, pipeline)
    return imported


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

    legacy_workspace = config.get("schema_version") != "2.0" or any(
        key in config for key in ("operating_mode", "limits", "goals", "plugin_version")
    )
    if legacy_workspace:
        legacy_goals = config.get("goals", {})
        primary_goal = legacy_goals.get("primary") if isinstance(legacy_goals, dict) else None
        if isinstance(primary_goal, str):
            match = re.search(r"from\s+([\d,]+)\s+to\s+([\d,]+)", primary_goal, re.IGNORECASE)
            if match:
                target = config.setdefault("target", json.loads(json.dumps(defaults["target"])))
                target["metric_a"].update(
                    {
                        "baseline": int(match.group(1).replace(",", "")),
                        "goal": int(match.group(2).replace(",", "")),
                        "goal_mode": "absolute",
                    }
                )
        legacy_focus = config.get("content_focus", {})
        if isinstance(legacy_focus, dict):
            niche = legacy_focus.get("niche")
            if niche:
                config.setdefault("audience", {})["niche"] = niche

    legacy_fixed_keys = {
        "windows_per_day",
        "max_actions_per_window",
        "gap_clusters_per_day",
        "max_action_clusters_per_day",
        "max_actions_per_cluster",
        "max_actions_per_day",
        "min_proactive_cluster_gap_minutes",
        "posts_per_day",
        "minimum_posts_per_day",
        "maximum_posts_per_day",
        "prepared_packages_per_content_day",
        "base_actions_per_day",
    }
    config["schema_version"] = "2.0"
    fixed = config.setdefault("fixed_rules", {})
    for key in legacy_fixed_keys:
        fixed.pop(key, None)
    fixed.update(
        {
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
    )
    engagement = config.setdefault("engagement_optimization", {})
    engagement.pop("clusters", None)
    adaptive_dispatch = config.setdefault("adaptive_dispatch", {})
    adaptive_dispatch["priority_order"] = list(defaults["adaptive_dispatch"]["priority_order"])
    merged, merged_missing = merge_missing(config, defaults)
    merged["schema_version"] = "2.0"
    merged["fixed_rules"] = fixed
    merged["opportunity_recovery"]["daily_action_milestones"] = list(
        defaults["opportunity_recovery"]["daily_action_milestones"]
    )
    merged["automation_reliability"]["reserve"].update(
        {"min_target": 40, "max_target": 80}
    )
    browser_rules = merged["automation_reliability"].setdefault("browser_binding", {})
    browser_rules.pop("routine_device_questions_allowed", None)
    browser_rules["direct_pinned_device_selection"] = True
    merged["publishing_optimization"].update(defaults["publishing_optimization"])
    merged.setdefault("autonomous_execution", {})["mode"] = defaults[
        "autonomous_execution"
    ]["mode"]
    autonomous_execution = merged.setdefault("autonomous_execution", {})
    autonomous_execution.pop("host_interactive_fallback_allowed", None)
    autonomous_execution.pop("owner_or_observer_approval_fallback_allowed", None)
    autonomous_execution.setdefault("interactive_fallback_enabled", False)
    autonomous_execution.setdefault("interactive_mutation_fallback_enabled", False)
    for section in ("regional_intelligence", "content_research", "analytics_contract", "runtime_repair"):
        merged[section] = defaults[section]
    for obsolete_key in (
        "plugin_version",
        "operating_mode",
        "limits",
        "goals",
        "content_focus",
        "owner",
        "producer",
        "created_at",
        "lifecycle_state",
        "next_trigger",
        "validation_status",
    ):
        merged.pop(obsolete_key, None)
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
        state["schema_version"] = "2.0"
        runtime_instructions = state.setdefault("runtime_instructions", {})
        runtime_instructions["active_version"] = CURRENT_VERSION
        runtime_instructions["detected_version"] = CURRENT_VERSION
        runtime_instructions["session_version"] = CURRENT_VERSION
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
            "rolling_24h_actions": 0,
            "rolling_action_target": 160,
            "rolling_action_cap": 200,
            "action_debt": 160,
            "base_daily_ceiling": 200,
            "base_actions_used": 0,
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
                "packages_required": 6,
                "packages_ready": min(max(int(publishing.get("packages_ready", package_count) or 0), 0), 6),
                "posts_published": 0,
                "rolling_24h_posts": 0,
                "rolling_post_target": 6,
                "rolling_post_cap": 8,
                "post_debt": 6,
                "rolling_inventory_target": 6,
                "normal_posts_published": min(max(int(publishing.get("normal_posts_published", published_count) or 0), 0), 6),
                "recovery_posts_published": min(max(int(publishing.get("recovery_posts_published", 0) or 0), 0), 2),
                "published_post_ids": publishing.get("published_post_ids", []),
                "last_publication_at": publishing.get("last_publication_at"),
                "current_cannibalization_signal": publishing.get("current_cannibalization_signal"),
            }
        )
        state["publishing"] = publishing
        continuation = state.setdefault("dispatcher", {}).setdefault("continuation", {})
        continuation.pop("expires_at", None)
        continuation.pop("fixed_expiry_at", None)
        continuation.pop("owner_input_required", None)
        continuation.pop("campaign_completion_or_owner_stop_required_to_end", None)
        continuation.update(
            {
                "mode": "automatic",
                "setup_input_required": False,
                "dedupe_key": f"linkedin-campaign-continuation:{campaign_id}",
                "expiry_policy": "renew-before-host-limit-until-target-or-stop-signal",
                "renew_existing_automation": True,
                "renewal_due_before_expiry": True,
                "campaign_completion_or_stop_signal_required_to_end": True,
            }
        )
        browser_binding = state.setdefault("dispatcher", {}).setdefault("browser_binding", {})
        browser_binding["selection_policy"] = "reuse-pinned-device-directly"
        execution_state = state.setdefault("autonomous_execution", {})
        legacy_ready = execution_state.pop("zero_human_ready", None)
        if "unattended_ready" not in execution_state and isinstance(legacy_ready, bool):
            execution_state["unattended_ready"] = legacy_ready
        execution_state.pop("observer_input_required", None)
        execution_state.pop("owner_input_required", None)
        if "automation_readiness" in state and "executor_readiness" not in state:
            state["executor_readiness"] = state.pop("automation_readiness")
        else:
            state.pop("automation_readiness", None)
        merged_state, state_updated = merge_missing(state, state_defaults)
        for obsolete_key in (
            "plugin_version",
            "lifecycle",
            "next_trigger",
            "producer",
            "profile_binding",
            "controller_links",
            "stage_history",
            "created_at",
            "last_updated",
        ):
            merged_state.pop(obsolete_key, None)
        state_updated = state_updated or merged_state != load_object(state_path)
        if state_updated:
            atomic_write_json(state_path, merged_state)
        state = merged_state

    created: list[str] = []
    consent_path = state_dir / "consent-record.json"
    if not consent_path.is_file():
        consent = load_object(assets_dir / "consent-record.template.json")
        identity: dict[str, Any] = {}
        for identity_path in (
            state_dir / "brand" / "brand-profile.json",
            state_dir / "brand-profile.json",
        ):
            if identity_path.is_file():
                try:
                    identity = load_object(identity_path)
                except (OSError, json.JSONDecodeError, ValueError):
                    identity = {}
                if identity.get("display_name") and identity.get("profile_url"):
                    break
        legacy_owner = original_config.get("owner", {})
        if not isinstance(legacy_owner, dict):
            legacy_owner = {}
        display_name = identity.get("display_name") or legacy_owner.get("display_name")
        profile_url = identity.get("profile_url") or legacy_owner.get("profile_url")
        consent["campaign_id"] = campaign_id
        consent["data_directory"] = str(state_dir)
        if display_name and profile_url:
            consent["owner"] = {
                "display_name": display_name,
                "expected_linkedin_identity": display_name,
            }
            consent["accounts"] = [
                {
                    "type": "linkedin-profile",
                    "owner": display_name,
                    "url": profile_url,
                }
            ]
        atomic_write_json(consent_path, consent)
        created.append(consent_path.name)
    consent_updated = False
    if consent_path.is_file():
        consent = load_object(consent_path)
        legacy_receipt = consent.pop("authorization_receipt", None)
        if "operating_receipt" not in consent and isinstance(legacy_receipt, dict):
            consent["operating_receipt"] = legacy_receipt
        legacy_classes = consent.pop("approved_action_classes", None)
        configured_classes = consent.get("configured_action_classes", [])
        if not isinstance(configured_classes, list):
            configured_classes = []
        if isinstance(legacy_classes, list):
            configured_classes = list(dict.fromkeys([*configured_classes, *legacy_classes]))
        legacy_account_classes = {
            "chrome-preflight",
            "engagement-queue-preparation",
            "linkedin-read",
            "linkedin-publish",
            "linkedin-comment",
            "linkedin-reply",
            "linkedin-direct-message",
            "linkedin-reaction",
            "linkedin-connection-request",
            "signal-reciprocity",
        }
        configured_classes = [
            value for value in configured_classes if value not in legacy_account_classes
        ]
        local_action_classes = [
            "profile-read-verification",
            "research",
            "content-drafting",
            "asset-production",
            "conversation-opportunity-planning",
            "service-request-preparation",
            "service-capability-recheck",
            "adaptive-scheduling",
            "opportunity-recovery",
            "performance-recovery-content",
            "analytics",
            "state-and-log-updates",
        ]
        legacy_renewal = consent.pop("reconfirmation_policy", None)
        if "renewal_policy" not in consent and isinstance(legacy_renewal, dict):
            consent["renewal_policy"] = legacy_renewal
        renewal_policy = consent.setdefault("renewal_policy", {})
        if not isinstance(renewal_policy, dict):
            renewal_policy = {}
            consent["renewal_policy"] = renewal_policy
        legacy_routine = renewal_policy.pop("routine_reconfirmation_required", None)
        if "routine_renewal_required" not in renewal_policy and isinstance(legacy_routine, bool):
            renewal_policy["routine_renewal_required"] = legacy_routine
        legacy_triggers = renewal_policy.pop("reask_only_when", None)
        if "renew_only_when" not in renewal_policy and isinstance(legacy_triggers, list):
            renewal_policy["renew_only_when"] = legacy_triggers
        legacy_stop_signals = consent.pop("owner_stop_signals", None)
        if "campaign_stop_signals" not in consent and isinstance(legacy_stop_signals, list):
            consent["campaign_stop_signals"] = legacy_stop_signals
        required_settings = [
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
        ]
        current_settings = consent.get("persistent_settings", [])
        if not isinstance(current_settings, list):
            current_settings = []
        obsolete_settings = {
            "adaptive-80-action-ceiling",
            "adaptive-100-base-action-ceiling",
            "adaptive-two-to-six-publications",
            "one-time-high-value-consent",
            "campaign-lifetime-consent-reload",
            "automatic-recovery-without-routine-questions",
            "automated-mode",
            "rolling-160-action-target-200-cap",
            "continuous-24-hour-dispatch",
            "direct-inbound-overage",
            "fully-dynamic-publishing",
            "permanent-dominant-gif-learning-deletion",
            "six-to-eight-rolling-publications",
            "relationship-only-proactive-dms",
        }
        current_settings = [value for value in current_settings if value not in obsolete_settings]
        merged_settings = list(dict.fromkeys([*current_settings, *required_settings]))
        receipt = consent.get("operating_receipt", {})
        receipt_missing = not isinstance(receipt, dict) or not receipt.get("receipt_id")
        receipt_mode_stale = (
            isinstance(receipt, dict)
            and receipt.get("automation_mode") != "automatic-local-workspace"
        )
        owner = consent.get("owner", {})
        owner_name = owner.get("display_name") if isinstance(owner, dict) else None
        needs_update = (
            consent.get("consent_version") != "2.0"
            or consent.get("schema_version") != "2.0"
            or merged_settings != current_settings
            or configured_classes != consent.get("configured_action_classes")
            or legacy_receipt is not None
            or legacy_classes is not None
            or legacy_renewal is not None
            or legacy_routine is not None
            or legacy_triggers is not None
            or legacy_stop_signals is not None
            or receipt_mode_stale
            or (consent.get("status") == "active" and receipt_missing)
        )
        if needs_update:
            consent["schema_version"] = "2.0"
            consent["consent_version"] = "2.0"
            consent["scope"] = "campaign-lifetime"
            consent["persistent_settings"] = merged_settings
            consent["configured_action_classes"] = list(
                dict.fromkeys([*configured_classes, *local_action_classes])
            )
            if isinstance(consent.get("operating_receipt"), dict):
                consent["operating_receipt"]["automation_mode"] = (
                    "automatic-local-workspace"
                )
            if consent.get("status") == "active" and receipt_missing:
                if not owner_name or owner_name == "replace-me":
                    consent["status"] = "pending"
                else:
                    granted_at = consent.get("activated_at") or datetime.now(timezone.utc).isoformat()
                    consent["activated_at"] = granted_at
                    consent["operating_receipt"] = {
                        "receipt_id": f"consent-{campaign_id}-migrated",
                        "granted_at": granted_at,
                        "granted_by": owner_name,
                        "source": "migrated-existing-explicit-owner-consent",
                        "automation_mode": "automatic-local-workspace",
                        "portable_across_model_sessions": True,
                    }
            consent["renewal_policy"] = {
                "routine_renewal_required": False,
                "reload_on_every_session_start": True,
                "renew_only_when": [
                    "owner-revoked",
                    "consent-record-missing-or-invalid",
                    "verified-account-identity-changed",
                ],
            }
            atomic_write_json(consent_path, consent)
            consent_updated = True

    executor_path = state_dir / "external-executor.json"
    executor_template = load_object(assets_dir / "external-executor.template.json")
    if not executor_path.exists():
        executor = executor_template
        executor["campaign_id"] = campaign_id
        created.append(executor_path.name)
    else:
        executor = load_object(executor_path)
        legacy_unattended = executor.pop("zero_human", None)
        if "unattended" not in executor and isinstance(legacy_unattended, bool):
            executor["unattended"] = legacy_unattended
        legacy_interactive = executor.pop("host_interactive_fallback_allowed", None)
        if "interactive_fallback_enabled" not in executor and isinstance(legacy_interactive, bool):
            executor["interactive_fallback_enabled"] = legacy_interactive
        executor.pop("owner_or_observer_approval_fallback_allowed", None)
        executor.pop("observer_input_required", None)
        executor.pop("owner_input_required", None)
        for key, value in executor_template.items():
            executor.setdefault(key, value)
        source = executor.setdefault("credential_source", {})
        template_source = executor_template.get("credential_source", {})
        if isinstance(source, dict) and isinstance(template_source, dict):
            source["type"] = "environment-or-macos-keychain"
            for key, value in template_source.items():
                source.setdefault(key, value)
            keychain = source.setdefault("keychain", {})
            template_keychain = template_source.get("keychain", {})
            if isinstance(keychain, dict) and isinstance(template_keychain, dict):
                for key, value in template_keychain.items():
                    keychain.setdefault(key, value)
    executor["campaign_id"] = campaign_id
    accounts = executor.get("credential_source", {}).get("keychain", {}).get("accounts", {})
    if isinstance(accounts, dict):
        for key in list(accounts):
            if not isinstance(accounts[key], str) or accounts[key].startswith("replace-me:"):
                accounts[key] = f"{campaign_id}:{key.replace('_', '-')}"
    atomic_write_json(executor_path, executor)
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
            "schema_version": "2.0",
            "campaign_id": campaign_id,
            "updated_at": None,
            "items": [],
        },
        "stage-ledger.json": {
            "schema_version": "2.0",
            "campaign_id": campaign_id,
            "updated_at": None,
            "stages": [],
        },
        "engagement-opportunities.json": {
            "schema_version": "2.0",
            "campaign_id": campaign_id,
            "updated_at": None,
            "opportunities": [],
        },
        "operational-output.json": {
            "schema_version": "2.0",
            "campaign_id": campaign_id,
            "calculated_at": None,
            "actions": {"rolling_24h_actions": 0, "target": 160, "hard_cap": 200, "debt": 160},
            "publishing": {"rolling_24h_posts": 0, "target": 6, "hard_cap": 8, "debt": 6},
        },
        "content-pipeline.json": {
            "schema_version": "2.0",
            "campaign_id": campaign_id,
            "topic_candidates": [],
            "briefs": [],
            "packages": [],
            "inventory": {"target": 6, "validated_unpublished": 0, "debt": 6},
            "analytics_schedule": [],
            "replacement_requirements": [],
        },
        "regional-performance.json": {
            "schema_version": "2.0",
            "campaign_id": campaign_id,
            "observations": [],
            "current_allocation": {
                "mode": "bootstrap",
                "six_post_allocation": ["india", "india", "us", "us", "uk-eu", "apac"],
                "observation_count": 0,
            },
            "exploration_state": {"proven": 70, "promising": 20, "exploration": 10},
        },
        "repair-state.json": {
            "schema_version": "2.0",
            "campaign_id": campaign_id,
            "status": "healthy",
            "active_repair": None,
            "history": [],
        },
    }
    for name, initial in artifacts.items():
        path = state_dir / name
        if not path.exists():
            atomic_write_json(path, initial)
            created.append(name)
    queue_path = state_dir / "work-queue.json"
    queue = load_object(queue_path)
    queue_changed = False
    legacy_task_count = 0
    if legacy_workspace:
        legacy_tasks = queue.pop("tasks", [])
        if isinstance(legacy_tasks, list) and legacy_tasks:
            legacy_task_count = len(legacy_tasks)
            atomic_write_json(
                state_dir / "legacy-task-index.json",
                {
                    "schema_version": "1.0",
                    "campaign_id": campaign_id,
                    "source_version": original_config.get("plugin_version"),
                    "tasks": [
                        {
                            "task_id": item.get("task_id"),
                            "status": item.get("status"),
                            "evidence": item.get("evidence", []),
                        }
                        for item in legacy_tasks
                        if isinstance(item, dict)
                    ],
                },
            )
            created.append("legacy-task-index.json")
            queue_changed = True
    for item in queue.get("items", []):
        if not isinstance(item, dict):
            continue
        legacy_contract = item.pop("execution_authorization", None)
        if "dispatch_contract" not in item and isinstance(legacy_contract, dict):
            item["dispatch_contract"] = legacy_contract
        if legacy_contract is not None:
            queue_changed = True
    if queue_changed:
        atomic_write_json(queue_path, queue)
    regional_path = state_dir / "regional-performance.json"
    regional = load_object(regional_path)
    merged_regional, _ = merge_missing(regional, artifacts["regional-performance.json"])
    merged_regional["schema_version"] = "2.0"
    merged_regional["campaign_id"] = campaign_id
    current_allocation = merged_regional.setdefault("current_allocation", {})
    current_allocation.setdefault("observation_count", 0)
    atomic_write_json(regional_path, merged_regional)
    repair_path = state_dir / "repair-state.json"
    repair = load_object(repair_path)
    merged_repair, _ = merge_missing(repair, artifacts["repair-state.json"])
    merged_repair["schema_version"] = "2.0"
    merged_repair["campaign_id"] = campaign_id
    atomic_write_json(repair_path, merged_repair)
    migration_now = current_time(args.now)
    imported_opportunities = import_legacy_opportunities(state_dir, campaign_id, migration_now)
    imported_packages = import_legacy_packages(state_dir, campaign_id, migration_now)
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
        "opportunity-health.jsonl",
        "repair-events.jsonl",
        "external-executor-events.jsonl",
    ):
        path = state_dir / name
        if not path.exists():
            path.touch()
            created.append(path.name)
    for status in ("pending", "running", "verified", "deferred", "ambiguous", "failed"):
        path = state_dir / "external-action-outbox" / status
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            created.append(str(path.relative_to(state_dir)))

    algorithm_path = state_dir / "working-algorithm-model.json"
    algorithm_defaults = {
        "schema_version": "2.0",
        "campaign_id": campaign_id,
        "version": CURRENT_VERSION,
        "strategy_weights": {"proven": 70, "promising": 20, "exploration": 10},
        "scheduling_models": {
            "publication_timing": {"mode": "evidence-adaptive", "observations": []},
            "response_latency": {"mode": "evidence-adaptive", "observations": []},
            "regional_opportunity": {"mode": "evidence-adaptive", "observations": []},
            "concentration": {"mode": "evidence-adaptive", "observations": []},
            "candidate_staleness": {"mode": "evidence-adaptive", "observations": []},
            "source_yield": {"mode": "evidence-adaptive", "observations": []},
            "gate_tier": {"mode": "evidence-adaptive", "observations": []},
            "action_type": {"mode": "evidence-adaptive", "observations": []},
            "recovery_post": {"mode": "evidence-adaptive", "observations": []},
            "action_to_profile_view": {"mode": "evidence-adaptive", "observations": []},
            "follower_conversion": {"mode": "evidence-adaptive", "observations": []},
            "format_performance": {"mode": "evidence-adaptive", "observations": []},
            "topic_performance": {"mode": "evidence-adaptive", "observations": []},
            "regional_spillover": {"mode": "evidence-adaptive", "observations": []},
        },
        "hypotheses": [],
    }
    if algorithm_path.exists():
        algorithm = load_object(algorithm_path)
        merged_algorithm, algorithm_updated = merge_missing(algorithm, algorithm_defaults)
        merged_algorithm["schema_version"] = "2.0"
        merged_algorithm["version"] = CURRENT_VERSION
        if algorithm_updated or merged_algorithm != algorithm:
            atomic_write_json(algorithm_path, merged_algorithm)
    else:
        atomic_write_json(algorithm_path, algorithm_defaults)
        created.append(algorithm_path.name)

    state = load_object(state_path) if state_path.is_file() else {}
    queue_path = state_dir / "work-queue.json"
    queue = load_object(queue_path)
    queue["schema_version"] = "2.0"
    queue["campaign_id"] = campaign_id
    items = queue.get("items", [])
    if not isinstance(items, list):
        items = []
    existing_task_ids = {item.get("task_id") for item in items if isinstance(item, dict)}
    for item in items:
        if (
            isinstance(item, dict)
            and item.get("task_type") == "adaptive-reserve"
            and item.get("status") not in {"completed", "superseded", "expired", "cancelled"}
        ):
            item["status"] = "superseded"
            item["completion_reason"] = "migrated-to-canonical-opportunity-generation"
    publishing = state.get("publishing", {})
    for item in items:
        if not isinstance(item, dict) or item.get("status") in {"completed", "superseded", "expired", "cancelled"}:
            continue
        if item.get("task_type") in {"two-package-production", "performance-recovery-content"}:
            item["status"] = "superseded"
            item["completion_reason"] = "migrated-to-six-package-rolling-pipeline"
    if publishing.get("packages_ready", 0) < 6 and "six-package-replenishment" not in existing_task_ids:
        items.append(
            {
                "task_id": "six-package-replenishment",
                "task_type": "six-package-replenishment",
                "lane": "offline",
                "priority": 5,
                "status": "pending",
                "ready": True,
                "requires_linkedin": False,
                "target_scope": "rolling-inventory",
                "required_regions": config.get("publishing_optimization", {}).get(
                    "required_regions", ["india", "india", "us", "us", "uk-eu", "apac"]
                ),
                "required_package_count": 6,
                "topic_candidate_target": 12,
                "normal_package_limit": 6,
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
    ledger["schema_version"] = "2.0"
    ledger["campaign_id"] = campaign_id
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
                "schema_version": "2.0",
                "plugin_version": CURRENT_VERSION,
                "config_updated": changed,
                "state_updated": state_updated,
                "consent_updated": consent_updated,
                "created": created,
                "imported_opportunities": imported_opportunities,
                "imported_packages": imported_packages,
                "legacy_tasks_indexed": legacy_task_count,
                "runtime_reconciliation": runtime_reconciliation,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
