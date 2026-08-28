#!/usr/bin/env python3
"""Deterministic opportunity-health and canonical engagement-queue helpers."""

from __future__ import annotations

import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


DEFAULT_WEIGHTS = {
    "equal_age_impressions": 0.25,
    "engagement_rate": 0.20,
    "profile_view_velocity": 0.20,
    "follower_connection_growth": 0.10,
    "action_pace": 0.15,
    "reserve_coverage_yield": 0.10,
}
DEFAULT_MILESTONES = [
    {"day_fraction": 0.25, "actions": 40},
    {"day_fraction": 0.50, "actions": 80},
    {"day_fraction": 0.75, "actions": 120},
    {"day_fraction": 1.00, "actions": 160},
]
DEFAULT_TIERS = {
    "normal": {"minimum_score": 65, "new_target_min_followers": 3000, "cooldown_hours": 72},
    "expansion": {"minimum_score": 60, "new_target_min_followers": 2000, "cooldown_hours": 48},
    "intensive": {"minimum_score": 55, "new_target_min_followers": 1000, "cooldown_hours": 24},
}
DEFAULT_SOURCES = [
    "direct-inbound-and-notifications",
    "own-post-signals",
    "existing-targets-and-hubs",
    "hub-post-commenters-and-reactors",
    "regional-and-topic-search",
    "premium-searches-alerts-newsletters-events",
    "second-degree-and-new-connections",
    "creator-registry-adjacency-trends-primary-sources",
]
ELIGIBLE_STATUSES = {"qualified", "ready"}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            records.append(value)
    return records


def opportunity_document(state_dir: Path, campaign_id: str | None = None) -> dict[str, Any]:
    path = state_dir / "engagement-opportunities.json"
    if path.is_file():
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or not isinstance(value.get("opportunities"), list):
            raise ValueError("engagement-opportunities.json must contain an opportunities array")
        return value
    return {
        "schema_version": "2.0",
        "campaign_id": campaign_id,
        "updated_at": None,
        "opportunities": [],
    }


def recovery_config(config: dict[str, Any]) -> dict[str, Any]:
    supplied = config.get("opportunity_recovery", {})
    return supplied if isinstance(supplied, dict) else {}


def tiers(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    configured = recovery_config(config).get("tiers", {})
    result: dict[str, dict[str, Any]] = {}
    for name, default in DEFAULT_TIERS.items():
        current = configured.get(name, {}) if isinstance(configured, dict) else {}
        result[name] = {**default, **(current if isinstance(current, dict) else {})}
    return result


def active_tier(state: dict[str, Any], config: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    recovery = state.setdefault("opportunity_recovery", {})
    mode = str(recovery.get("mode") or "normal")
    configured = tiers(config)
    if mode not in configured:
        mode = "normal"
    floor = configured[mode]
    # These are immutable safety/quality floors of the operating model.
    floor["minimum_score"] = max(55, float(floor.get("minimum_score", 65)))
    floor["new_target_min_followers"] = max(
        1000, int(floor.get("new_target_min_followers", 3000))
    )
    floor["cooldown_hours"] = max(24, int(floor.get("cooldown_hours", 72)))
    return mode, floor


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def eligible_opportunities(
    document: dict[str, Any],
    state: dict[str, Any],
    config: dict[str, Any],
    now: datetime,
) -> list[dict[str, Any]]:
    mode, gate = active_tier(state, config)
    selected: list[dict[str, Any]] = []
    seen_soft_targets: set[str] = set()
    for raw in document.get("opportunities", []):
        if not isinstance(raw, dict) or raw.get("status") not in ELIGIBLE_STATUSES:
            continue
        lane = str(raw.get("lane") or "proactive")
        if lane not in {"proactive", "soft-reciprocity", "direct-inbound"}:
            continue
        expires = _parse_time(raw.get("expires_at") or raw.get("expiry"))
        not_before = _parse_time(raw.get("not_before"))
        if expires is not None and expires <= now:
            continue
        if not_before is not None and not_before > now:
            continue
        if raw.get("action_available", True) is not True:
            continue
        if lane != "direct-inbound":
            scaling = state.get("engagement_scaling", {})
            if int(scaling.get("rolling_24h_actions", scaling.get("base_actions_used", 0)) or 0) >= int(
                scaling.get("rolling_action_cap", scaling.get("base_daily_ceiling", 200)) or 200
            ):
                continue
            score = raw.get("score", raw.get("action_score", 0))
            if isinstance(score, bool) or not isinstance(score, (int, float)) or score < gate["minimum_score"]:
                continue
            if raw.get("cooldown_passed") is not True:
                continue
            if raw.get("target_status") == "new":
                followers = raw.get("follower_count")
                if isinstance(followers, bool) or not isinstance(followers, (int, float)):
                    continue
                if followers < gate["new_target_min_followers"]:
                    continue
            weekly = raw.get("proactive_actions_person_7d", 0)
            if isinstance(weekly, bool) or not isinstance(weekly, (int, float)) or weekly >= 2:
                continue
            action_type = str(raw.get("action_type") or "").lower()
            if action_type in {"dm", "message", "direct-message"}:
                if raw.get("connection_status") not in {"existing", "connected"}:
                    continue
                prior_evidence = raw.get("prior_interaction_evidence")
                if prior_evidence is not True and not isinstance(prior_evidence, dict):
                    continue
        if lane == "soft-reciprocity":
            target = str(raw.get("candidate_identity") or raw.get("target_id") or raw.get("candidate_id"))
            if target in seen_soft_targets:
                continue
            seen_soft_targets.add(target)
        item = dict(raw)
        item["active_gate_tier"] = mode
        selected.append(item)
    lane_priority = {"direct-inbound": 0, "soft-reciprocity": 1, "proactive": 2}
    selected.sort(
        key=lambda item: (
            lane_priority.get(str(item.get("lane")), 3),
            -float(item.get("score", item.get("action_score", 0)) or 0),
            str(item.get("candidate_id", "")),
        )
    )
    return selected


def expected_actions(now: datetime, timezone_name: str, milestones: list[dict[str, Any]]) -> float:
    local = now.astimezone(ZoneInfo(timezone_name))
    fraction = (local.hour * 3600 + local.minute * 60 + local.second) / 86400
    points = [(0.0, 0.0)] + sorted(
        (float(item["day_fraction"]), float(item["actions"]))
        for item in milestones
        if isinstance(item, dict)
    )
    for (left_x, left_y), (right_x, right_y) in zip(points, points[1:]):
        if fraction <= right_x:
            span = right_x - left_x
            return left_y if span <= 0 else left_y + ((fraction - left_x) / span) * (right_y - left_y)
    return points[-1][1]


def _number(record: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value: Any = record
        for part in key.split("."):
            value = value.get(part) if isinstance(value, dict) else None
        if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value)):
            return float(value)
    return None


def _score_ratio(current: float | None, baseline: float | None) -> float | None:
    if current is None or baseline is None or baseline <= 0:
        return None
    return max(0.0, min(100.0, current / baseline * 100.0))


def _metric_series(records: list[dict[str, Any]], keys: tuple[str, ...]) -> list[float]:
    values: list[float] = []
    for record in records:
        value = _number(record, *keys)
        if value is not None:
            values.append(value)
    return values


def evaluate_health(
    state_dir: Path,
    state: dict[str, Any],
    config: dict[str, Any],
    now: datetime,
) -> dict[str, Any]:
    settings = recovery_config(config)
    weights = settings.get("health_weights", DEFAULT_WEIGHTS)
    if not isinstance(weights, dict) or set(weights) != set(DEFAULT_WEIGHTS):
        weights = DEFAULT_WEIGHTS
    analytics = read_jsonl(state_dir / "daily-analytics.jsonl")[-64:]
    current = analytics[-1] if analytics else {}
    history = analytics[:-1]
    current_age = _number(current, "age_minutes", "post_age_minutes", "metrics.age_minutes")
    current_region = current.get("region") or current.get("target_region")
    if current_age is not None:
        tolerance = max(30.0, current_age * 0.20)
        history = [
            record for record in history
            if (candidate_age := _number(record, "age_minutes", "post_age_minutes", "metrics.age_minutes")) is not None
            and abs(candidate_age - current_age) <= tolerance
            and (not current_region or (record.get("region") or record.get("target_region")) in {None, current_region})
        ]
    history = history[-7:]
    impressions_history = _metric_series(history, ("impressions", "metrics.impressions"))
    engagement_history = _metric_series(history, ("engagement_rate", "metrics.engagement_rate"))
    profile_history = _metric_series(history, ("profile_view_velocity", "profile_views_velocity", "metrics.profile_view_velocity"))
    growth_history = _metric_series(history, ("follower_connection_growth", "growth_velocity", "metrics.follower_connection_growth"))
    median = lambda values: statistics.median(values) if values else None
    components: dict[str, float | None] = {
        "equal_age_impressions": _score_ratio(
            _number(current, "impressions", "metrics.impressions"), median(impressions_history)
        ),
        "engagement_rate": _score_ratio(
            _number(current, "engagement_rate", "metrics.engagement_rate"), median(engagement_history)
        ),
        "profile_view_velocity": _score_ratio(
            _number(current, "profile_view_velocity", "profile_views_velocity", "metrics.profile_view_velocity"),
            median(profile_history),
        ),
        "follower_connection_growth": _score_ratio(
            _number(current, "follower_connection_growth", "growth_velocity", "metrics.follower_connection_growth"),
            median(growth_history),
        ),
    }
    configured_milestones = settings.get("daily_action_milestones", DEFAULT_MILESTONES)
    milestones = configured_milestones if isinstance(configured_milestones, list) else DEFAULT_MILESTONES
    expected = expected_actions(now, str(config.get("timezone") or "UTC"), milestones)
    scaling = state.get("engagement_scaling", {})
    actual = int(scaling.get("rolling_24h_actions", scaling.get("base_actions_used", 0)) or 0)
    pace_ratio = 1.0 if expected <= 0 else actual / expected
    components["action_pace"] = max(0.0, min(100.0, pace_ratio * 100))
    document = opportunity_document(state_dir, str(state.get("campaign_id") or ""))
    eligible_count = len(eligible_opportunities(document, state, config, now))
    reserve = state.get("engagement_scaling", {}).get("adaptive_reserve", {})
    target = max(1, int(reserve.get("target_count", 1) or 1))
    coverage = min(1.0, eligible_count / target)
    yield_value = reserve.get("discovery_yield_per_page")
    yield_score = coverage if not isinstance(yield_value, (int, float)) else min(1.0, max(0.0, float(yield_value) / 0.25))
    components["reserve_coverage_yield"] = ((coverage + yield_score) / 2) * 100
    available = {key: value for key, value in components.items() if value is not None}
    denominator = sum(float(weights[key]) for key in available)
    health = 0.0 if denominator <= 0 else sum(float(available[key]) * float(weights[key]) for key in available) / denominator
    comparable = max(len(impressions_history), len(engagement_history), len(profile_history), len(growth_history))
    confidence = min(1.0, comparable / 3) if comparable else 0.25
    recovery = state.setdefault("opportunity_recovery", {})
    previous_mode = str(recovery.get("mode") or "normal")
    activation_threshold = float(settings.get("activation_threshold", 70))
    exit_threshold = float(settings.get("exit_threshold", 80))
    low_health = health < activation_threshold
    low_health_streak = int(recovery.get("low_health_streak", 0) or 0) + 1 if low_health else 0
    pace_below_half = actual < expected * 0.5
    active = previous_mode != "normal"
    trigger = low_health_streak >= 2 or pace_below_half
    exit_good = health >= exit_threshold and pace_ratio >= 0.9
    exit_streak = int(recovery.get("exit_streak", 0) or 0) + 1 if exit_good else 0
    if active and exit_streak >= 2:
        mode = "normal"
    elif active or trigger:
        mode = "intensive" if health < 55 or pace_ratio < 0.35 else "expansion"
    else:
        mode = "normal"
    tier = tiers(config)[mode]
    evaluation = {
        "schema_version": "2.0",
        "campaign_id": state.get("campaign_id"),
        "evaluated_at": now.astimezone(timezone.utc).isoformat(),
        "health_score": round(health, 2),
        "confidence": round(confidence, 4),
        "comparable_observations": comparable,
        "components": {key: (round(value, 2) if value is not None else None) for key, value in components.items()},
        "weights_used": {key: weights[key] for key in available},
        "missing_metrics": [key for key, value in components.items() if value is None],
        "expected_actions": round(expected, 2),
        "actual_actions": actual,
        "pace_ratio": round(pace_ratio, 4),
        "eligible_opportunities": eligible_count,
        "reserve_target": target,
        "previous_mode": previous_mode,
        "mode": mode,
        "activation_triggered": trigger,
        "exit_streak": exit_streak,
        "active_gate": tier,
    }
    recovery.update(
        {
            "mode": mode,
            "active": mode != "normal",
            "health_score": round(health, 2),
            "health_confidence": round(confidence, 4),
            "low_health_streak": low_health_streak,
            "exit_streak": exit_streak,
            "expected_actions": round(expected, 2),
            "actual_actions": actual,
            "pace_ratio": round(pace_ratio, 4),
            "trigger_evidence": {
                "health_below_70_twice": low_health_streak >= 2,
                "actions_below_half_expected": pace_below_half,
            },
            "active_score_floor": tier["minimum_score"],
            "active_follower_floor": tier["new_target_min_followers"],
            "active_cooldown_hours": tier["cooldown_hours"],
            "canonical_candidate_count": eligible_count,
            "last_evaluated_at": evaluation["evaluated_at"],
            "next_reevaluation_trigger": "after-next-wake-publication-burst-analytics-or-generation-pass",
        }
    )
    return evaluation


def next_discovery_source(
    state: dict[str, Any],
    config: dict[str, Any],
    now: datetime | None = None,
    excluded_sources: set[str] | None = None,
) -> str | None:
    settings = recovery_config(config)
    sources = settings.get("source_rotation", DEFAULT_SOURCES)
    if not isinstance(sources, list) or not sources:
        sources = DEFAULT_SOURCES
    recovery = state.setdefault("opportunity_recovery", {})
    history = recovery.get("source_performance", {})
    if not isinstance(history, dict):
        history = {}
    previous = recovery.get("last_discovery_source")
    now = now or datetime.now(timezone.utc)
    excluded = excluded_sources or set()
    available = []
    for source in sources:
        source_name = str(source)
        if source_name in excluded:
            continue
        record = history.get(source_name, {})
        backoff_until = _parse_time(record.get("backoff_until")) if isinstance(record, dict) else None
        if backoff_until is None or backoff_until <= now:
            available.append(source_name)
    candidates = [source for source in available if source != previous] or available
    if not candidates:
        return None

    def source_score(source: str) -> tuple[float, int, str]:
        record = history.get(source, {})
        attempts = int(record.get("attempts", 0) or 0) if isinstance(record, dict) else 0
        accepted = int(record.get("accepted_candidates", 0) or 0) if isinstance(record, dict) else 0
        executed = int(record.get("actions_executed", 0) or 0) if isinstance(record, dict) else 0
        outcome = int(record.get("replies_generated", 0) or 0) + int(record.get("profile_views", 0) or 0) + int(record.get("follower_outcomes", 0) or 0) if isinstance(record, dict) else 0
        # 70/20/10 allocation is represented deterministically: proven outcome, promising yield, then unexplored.
        score = (0.70 * outcome + 0.20 * executed + 0.10 * (accepted / max(1, attempts)))
        return (-score, attempts, source)

    unexplored = [source for source in candidates if not history.get(source)]
    if unexplored:
        return unexplored[0]
    attempts_total = sum(
        int(record.get("attempts", 0) or 0)
        for record in history.values()
        if isinstance(record, dict)
    )
    allocation_slot = attempts_total % 10
    if allocation_slot < 7:
        group = [
            source for source in candidates
            if int(history.get(source, {}).get("actions_executed", 0) or 0) > 0
            or int(history.get(source, {}).get("replies_generated", 0) or 0) > 0
            or int(history.get(source, {}).get("profile_views", 0) or 0) > 0
            or int(history.get(source, {}).get("follower_outcomes", 0) or 0) > 0
        ]
    elif allocation_slot < 9:
        group = [
            source for source in candidates
            if int(history.get(source, {}).get("accepted_candidates", 0) or 0) > 0
        ]
    else:
        group = sorted(candidates, key=lambda source: int(history.get(source, {}).get("attempts", 0) or 0))[:1]
    return sorted(group or candidates, key=source_score)[0]
