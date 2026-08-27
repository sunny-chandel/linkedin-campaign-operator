#!/usr/bin/env python3
"""Select a publication opportunity from current evidence without fixed times or spacing."""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
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
    parser.add_argument("--state-dir", type=Path)
    parser.add_argument("--record", action="store_true", help="append to schedule-decisions.jsonl")
    args = parser.parse_args()
    if args.record and not args.state_dir:
        parser.error("--record requires --state-dir")
    try:
        data = json.loads(args.opportunities.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("input must contain a JSON object")
        posts = data.get("posts", [])
        opportunities = data.get("opportunities", [])
        if not isinstance(posts, list) or not isinstance(opportunities, list):
            raise ValueError("posts and opportunities must be arrays")
        if not 6 <= len(posts) <= 8:
            raise ValueError("between six and eight post records are required")
        normal_posts = [post for post in posts if isinstance(post, dict) and post.get("publication_kind", "normal") == "normal"]
        recovery_posts = [post for post in posts if isinstance(post, dict) and post.get("publication_kind") == "recovery"]
        regions = {str(post.get("region") or "") for post in normal_posts}
        if len(normal_posts) != 6:
            raise ValueError("normal portfolio must contain exactly six posts")
        if "india" not in regions or not ({"us", "us-central"} & regions):
            raise ValueError("normal portfolio must retain at least one India and one US post")
        pillars = {str(post.get("content_pillar") or "") for post in normal_posts} - {""}
        formats = {str(post.get("format_treatment") or post.get("format") or "") for post in normal_posts} - {""}
        if len(pillars) < 4 or len(formats) < 3:
            raise ValueError("six-post portfolio needs at least four pillars and three formats")
        for previous, current in zip(normal_posts, normal_posts[1:]):
            for field in ("topic", "angle"):
                if previous.get(field) and previous.get(field) == current.get(field):
                    raise ValueError(f"normal portfolio cannot repeat {field} consecutively")
            previous_format = previous.get("format_treatment") or previous.get("format")
            current_format = current.get("format_treatment") or current.get("format")
            if previous_format and previous_format == current_format:
                raise ValueError("normal portfolio cannot repeat format consecutively")
        unpublished_recovery = [post for post in recovery_posts if post.get("published") is not True]
        if len(unpublished_recovery) > 1:
            raise ValueError("at most one unpublished recovery package may be stored")
        published = [post for post in posts if post.get("published") is True]
        if len(published) >= 8:
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
                post = next((item for item in posts if item.get("post_id") == post_id), {})
                minutes_since_previous = opportunity.get("minutes_since_previous_publication")
                if published and (
                    isinstance(minutes_since_previous, bool)
                    or not isinstance(minutes_since_previous, (int, float))
                    or float(minutes_since_previous) < 120
                ):
                    continue
                if post.get("publication_kind") == "recovery":
                    if len([item for item in normal_posts if item.get("published") is True]) < 6:
                        continue
                    velocity = opportunity.get("preceding_post_velocity_ratio")
                    risk_value = opportunity.get("cannibalization_risk", 1)
                    velocity_low = isinstance(velocity, (int, float)) and not isinstance(velocity, bool) and velocity < 0.85
                    risk_low = isinstance(risk_value, (int, float)) and not isinstance(risk_value, bool) and risk_value < 0.35
                    if not (velocity_low or risk_low):
                        continue
                    if not all(
                        opportunity.get(key) is True
                        for key in ("fresh_source", "different_topic_angle", "different_pillar_or_format")
                    ):
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
                "absolute_minimum_spacing_minutes": 120,
                "publication_range": {"minimum": 6, "maximum": 8},
            }
        rendered = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            args.output.write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
        if args.record:
            state_dir = args.state_dir.expanduser().resolve()
            log_record = {
                **result,
                "decision_type": "publication",
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            }
            with (state_dir / "schedule-decisions.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(log_record, ensure_ascii=False) + "\n")
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
