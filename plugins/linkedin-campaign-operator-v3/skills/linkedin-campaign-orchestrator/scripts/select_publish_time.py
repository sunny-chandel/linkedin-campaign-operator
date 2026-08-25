#!/usr/bin/env python3
"""Select a publication opportunity from current evidence without fixed times or spacing."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


DEFAULT_WEIGHTS = {
    "regional_activity": 0.18,
    "qualified_target_activity": 0.14,
    "topic_freshness": 0.14,
    "network_velocity": 0.12,
    "previous_post_engagement_velocity": 0.12,
    "historical_equal_age": 0.18,
    "format_pillar_fit": 0.08,
    "remaining_day_opportunity": 0.04,
}


def bounded(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a number from 0 to 1")
    number = float(value)
    if not math.isfinite(number) or not 0 <= number <= 1:
        raise ValueError(f"{field} must be a number from 0 to 1")
    return number


def normalized_weights(data: dict[str, Any]) -> dict[str, float]:
    supplied = data.get("weights", DEFAULT_WEIGHTS)
    if not isinstance(supplied, dict) or set(supplied) != set(DEFAULT_WEIGHTS):
        raise ValueError("weights must contain the publication opportunity components")
    weights = {key: bounded(supplied[key], f"weights.{key}") for key in DEFAULT_WEIGHTS}
    if not math.isclose(sum(weights.values()), 1.0, abs_tol=1e-9):
        raise ValueError("weights must sum to 1.0")
    return weights


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("opportunities", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.opportunities.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("input must contain a JSON object")
        posts = data.get("posts", [])
        opportunities = data.get("opportunities", [])
        if not isinstance(posts, list) or not isinstance(opportunities, list):
            raise ValueError("posts and opportunities must be arrays")
        if len(posts) != 2:
            raise ValueError("exactly two prepared post records are required")
        required_regions = {"india", "us-central"}
        regions = {post.get("region") for post in posts if isinstance(post, dict)}
        if regions != required_regions:
            raise ValueError("prepared posts must contain exactly India and US-Central")
        published = [post for post in posts if post.get("published") is True]
        if len(published) >= 2:
            result = {
                "valid": True,
                "decision": "daily-publications-complete",
                "selected": None,
                "ranked": [],
            }
        else:
            ready_ids = {
                post.get("post_id")
                for post in posts
                if post.get("ready") is True and post.get("published") is not True
            }
            weights = normalized_weights(data)
            learning_allocation = data.get(
                "learning_allocation", {"proven": 70, "promising": 20, "exploration": 10}
            )
            if (
                not isinstance(learning_allocation, dict)
                or set(learning_allocation) != {"proven", "promising", "exploration"}
                or any(isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0 for value in learning_allocation.values())
                or learning_allocation != {"proven": 70, "promising": 20, "exploration": 10}
            ):
                raise ValueError("learning_allocation must be the 70/20/10 strategy allocation")
            penalty_weight = bounded(data.get("cannibalization_penalty_weight", 0.20), "cannibalization_penalty_weight")
            minimum_score = float(data.get("minimum_opportunity_score", 65))
            if not 0 <= minimum_score <= 100:
                raise ValueError("minimum_opportunity_score must be from 0 to 100")
            ranked: list[dict[str, Any]] = []
            for position, opportunity in enumerate(opportunities):
                if not isinstance(opportunity, dict):
                    raise ValueError(f"opportunities[{position}] must be an object")
                post_id = opportunity.get("post_id")
                if post_id not in ready_ids:
                    continue
                components = {
                    key: bounded(opportunity.get(key, 0), f"{post_id}.{key}")
                    for key in weights
                }
                risk = bounded(opportunity.get("cannibalization_risk", 0), f"{post_id}.cannibalization_risk")
                raw = sum(components[key] * weights[key] for key in weights) - risk * penalty_weight
                score = round(max(0.0, min(1.0, raw)) * 100, 2)
                ranked.append(
                    {
                        **opportunity,
                        "score_components": components,
                        "cannibalization_risk": risk,
                        "opportunity_score": score,
                    }
                )
            ranked.sort(
                key=lambda item: (
                    -item["opportunity_score"],
                    str(item.get("observed_at", "")),
                    str(item.get("post_id", "")),
                )
            )
            selected = ranked[0] if ranked else None
            publish_now = bool(
                selected
                and (
                    selected["opportunity_score"] >= minimum_score
                    or selected.get("last_remaining_opportunity") is True
                )
            )
            result = {
                "valid": True,
                "decision": "publish-now" if publish_now else "continue-investigation",
                "selected": selected if publish_now else None,
                "best_observed": selected,
                "ranked": ranked,
                "weights": weights,
                "minimum_opportunity_score": minimum_score,
                "learning_allocation": learning_allocation,
                "fixed_publish_time_used": False,
                "fixed_spacing_used": False,
            }
        rendered = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
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
