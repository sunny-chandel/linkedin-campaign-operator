#!/usr/bin/env python3
"""Create a deterministic utilization plan for verified subscription features."""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_WEIGHTS = {
    "campaign_relevance": 0.30,
    "unused_capacity": 0.25,
    "evidence_strength": 0.20,
    "expiry_urgency": 0.15,
    "implementation_readiness": 0.10,
}
DEFAULT_THRESHOLDS = {"activate_now": 70.0, "schedule": 45.0}


def bounded_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a number from 0 to 1")
    number = float(value)
    if not math.isfinite(number) or number < 0 or number > 1:
        raise ValueError(f"{field} must be a number from 0 to 1")
    return number


def normalized_weights(config: dict[str, Any]) -> dict[str, float]:
    supplied = config.get("weights", DEFAULT_WEIGHTS)
    if not isinstance(supplied, dict) or set(supplied) != set(DEFAULT_WEIGHTS):
        raise ValueError(f"weights must contain exactly: {', '.join(DEFAULT_WEIGHTS)}")
    weights = {key: bounded_number(supplied[key], f"weights.{key}") for key in DEFAULT_WEIGHTS}
    if not math.isclose(sum(weights.values()), 1.0, abs_tol=1e-9):
        raise ValueError("weights must sum to 1.0")
    return weights


def thresholds(config: dict[str, Any]) -> dict[str, float]:
    supplied = config.get("thresholds", DEFAULT_THRESHOLDS)
    if not isinstance(supplied, dict):
        raise ValueError("thresholds must be an object")
    activate_now = float(supplied.get("activate_now", DEFAULT_THRESHOLDS["activate_now"]))
    schedule = float(supplied.get("schedule", DEFAULT_THRESHOLDS["schedule"]))
    if not (0 <= schedule <= activate_now <= 100):
        raise ValueError("thresholds must satisfy 0 <= schedule <= activate_now <= 100")
    return {"activate_now": activate_now, "schedule": schedule}


def unused_capacity(feature: dict[str, Any]) -> tuple[float, str]:
    total = feature.get("quota_total")
    used = feature.get("quota_used")
    if (
        isinstance(total, (int, float))
        and not isinstance(total, bool)
        and isinstance(used, (int, float))
        and not isinstance(used, bool)
        and math.isfinite(float(total))
        and math.isfinite(float(used))
        and total > 0
        and used >= 0
    ):
        return max(0.0, min(1.0, (float(total) - float(used)) / float(total))), "verified-quota"
    explicit = feature.get("unused_capacity")
    if explicit is not None:
        return bounded_number(explicit, f"features.{feature.get('feature_id', '?')}.unused_capacity"), "observed"
    return 0.0, "unknown"


def score_feature(
    feature: dict[str, Any], weights: dict[str, float], limits: dict[str, float]
) -> dict[str, Any]:
    feature_id = feature.get("feature_id")
    if not isinstance(feature_id, str) or not feature_id.strip():
        raise ValueError("every feature requires a non-empty feature_id")
    entitled = feature.get("entitled") is True
    capacity, capacity_source = unused_capacity(feature)
    components = {
        "campaign_relevance": bounded_number(feature.get("campaign_relevance", 0), f"features.{feature_id}.campaign_relevance"),
        "unused_capacity": capacity,
        "evidence_strength": bounded_number(feature.get("evidence_strength", 0), f"features.{feature_id}.evidence_strength"),
        "expiry_urgency": bounded_number(feature.get("expiry_urgency", 0), f"features.{feature_id}.expiry_urgency"),
        "implementation_readiness": bounded_number(feature.get("implementation_readiness", 0), f"features.{feature_id}.implementation_readiness"),
    }
    score = round(sum(components[key] * weights[key] for key in weights) * 100, 2) if entitled else 0.0
    if not entitled:
        status = "unavailable"
    elif score >= limits["activate_now"]:
        status = "activate-now"
    elif score >= limits["schedule"]:
        status = "schedule"
    else:
        status = "monitor"
    return {
        "feature_id": feature_id,
        "name": feature.get("name", feature_id),
        "entitled": entitled,
        "configured": feature.get("configured") is True,
        "status": status,
        "score": score,
        "score_components": components,
        "unused_capacity_source": capacity_source,
        "pipeline_stages": feature.get("pipeline_stages", []),
        "expected_outcome": feature.get("expected_outcome"),
        "action_class": feature.get("action_class"),
        "counts_toward_window": feature.get("counts_toward_window") is True,
        "fallback": feature.get("fallback"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inventory", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--config", type=Path, help="campaign-config.json with subscription_optimization settings")
    args = parser.parse_args()

    try:
        inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
        config: dict[str, Any] = {}
        if args.config:
            campaign_config = json.loads(args.config.read_text(encoding="utf-8"))
            config = campaign_config.get("subscription_optimization", {})
        weights = normalized_weights(config)
        limits = thresholds(config)
        features = inventory.get("features", [])
        if not isinstance(features, list):
            raise ValueError("features must be an array")
        ranked = [score_feature(feature, weights, limits) for feature in features if isinstance(feature, dict)]
        ranked.sort(key=lambda item: (-item["score"], item["feature_id"]))
        plan = {
            "schema_version": "1.0",
            "campaign_id": inventory.get("campaign_id"),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_inventory": str(args.inventory),
            "weights": weights,
            "thresholds": limits,
            "features": ranked,
            "summary": {
                status: sum(1 for item in ranked if item["status"] == status)
                for status in ("activate-now", "schedule", "monitor", "unavailable")
            },
        }
        rendered = json.dumps(plan, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            args.output.write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
