#!/usr/bin/env python3
"""Rank eligible LinkedIn actions by predicted qualified-growth value."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


WEIGHTS = {
    "qualified_growth": 0.35,
    "audience_spillover": 0.20,
    "conversation_probability": 0.15,
    "target_relevance": 0.15,
    "freshness_timing": 0.10,
    "historical_performance": 0.05,
}
HARD_GATES = ("qualified", "cooldown_passed", "action_available", "capacity_available")


def bounded(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a number from 0 to 1")
    number = float(value)
    if not math.isfinite(number) or not 0 <= number <= 1:
        raise ValueError(f"{field} must be a number from 0 to 1")
    return number


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidates", type=Path)
    parser.add_argument("--threshold", type=float, default=65.0)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not 0 <= args.threshold <= 100:
        parser.error("threshold must be from 0 to 100")
    if not 1 <= args.limit <= 10:
        parser.error("limit must be from 1 to 10")

    try:
        data = json.loads(args.candidates.read_text(encoding="utf-8"))
        candidates = data.get("candidates", [])
        if not isinstance(candidates, list):
            raise ValueError("candidates must be an array")
        eligible: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        for position, candidate in enumerate(candidates):
            if not isinstance(candidate, dict):
                raise ValueError(f"candidates[{position}] must be an object")
            candidate_id = candidate.get("candidate_id")
            if not isinstance(candidate_id, str) or not candidate_id:
                raise ValueError(f"candidates[{position}].candidate_id must be set")
            failed_gates = [gate for gate in HARD_GATES if candidate.get(gate) is not True]
            if failed_gates:
                rejected.append({"candidate_id": candidate_id, "reason": "hard-gate", "failed_gates": failed_gates})
                continue
            components = {
                name: bounded(candidate.get(name, 0), f"{candidate_id}.{name}")
                for name in WEIGHTS
            }
            score = round(sum(components[name] * WEIGHTS[name] for name in WEIGHTS) * 100, 2)
            ranked = {**candidate, "score_components": components, "action_score": score}
            if score >= args.threshold:
                eligible.append(ranked)
            else:
                rejected.append({"candidate_id": candidate_id, "reason": "below-threshold", "action_score": score})
        eligible.sort(key=lambda item: (-item["action_score"], item["candidate_id"]))
        output = {
            "schema_version": "1.0",
            "campaign_id": data.get("campaign_id"),
            "threshold": args.threshold,
            "limit": args.limit,
            "selected": eligible[: args.limit],
            "eligible_not_selected": eligible[args.limit :],
            "rejected": rejected,
        }
        rendered = json.dumps(output, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            args.output.write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
