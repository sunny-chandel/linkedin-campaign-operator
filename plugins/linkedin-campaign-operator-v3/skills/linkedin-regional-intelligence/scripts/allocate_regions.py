#!/usr/bin/env python3
"""Select the six-post regional portfolio from durable performance evidence."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BOOTSTRAP = ["india", "india", "us", "us", "uk-eu", "apac"]
DEFAULT_EXPLORATION = ["uk-eu", "apac", "middle-east-africa", "latin-america"]


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain an object")
    return value


def allocation(state: dict[str, Any]) -> tuple[list[str], str]:
    observations = state.get("observations", [])
    if not isinstance(observations, list) or len(observations) < 12:
        return list(BOOTSTRAP), "bootstrap"
    scores: dict[str, float] = {}
    counts: dict[str, int] = {}
    for item in observations:
        if not isinstance(item, dict) or not isinstance(item.get("region"), str):
            continue
        region = item["region"]
        score = item.get("performance_score")
        if isinstance(score, (int, float)) and not isinstance(score, bool):
            scores[region] = scores.get(region, 0.0) + float(score)
            counts[region] = counts.get(region, 0) + 1
    averages = {region: scores[region] / counts[region] for region in scores}
    ranked = sorted(averages, key=lambda region: (-averages[region], region))
    core = ["india", "us"]
    for region in ranked:
        if region not in core and len(core) < 4:
            core.append(region)
    while len(core) < 4:
        core.append(DEFAULT_EXPLORATION[len(core) - 2])
    exploration = [region for region in DEFAULT_EXPLORATION if region not in core][:2]
    while len(exploration) < 2:
        exploration.append(f"exploration-{len(exploration) + 1}")
    return core[:4] + exploration, "evidence-adaptive-4-core-2-exploration"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state_dir", type=Path)
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()
    try:
        path = args.state_dir.expanduser().resolve() / "regional-performance.json"
        state = load_object(path)
        selected, mode = allocation(state)
        result = {
            "valid": True,
            "allocated_at": datetime.now(timezone.utc).isoformat(),
            "mode": mode,
            "six_post_allocation": selected,
            "india_posts": selected.count("india"),
            "us_posts": selected.count("us"),
            "core_count": 4 if mode != "bootstrap" else 4,
            "exploration_count": 2,
            "observation_count": len(state.get("observations", [])),
        }
        if result["india_posts"] < 1 or result["us_posts"] < 1 or len(selected) != 6:
            raise ValueError("regional allocation must contain six slots and retain India and US")
        if args.record:
            state["schema_version"] = "2.0"
            state["current_allocation"] = result
            state["updated_at"] = result["allocated_at"]
            path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2))
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
