#!/usr/bin/env python3
"""Rank normalized GIF reference records for per-post creative selection."""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


WEIGHTS = {
    "information_quality": 0.30,
    "normalized_engagement": 0.25,
    "visual_execution": 0.20,
    "recency": 0.15,
    "audience_fit": 0.10,
}


def bounded(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a number from 0 to 1")
    number = float(value)
    if not math.isfinite(number) or not 0 <= number <= 1:
        raise ValueError(f"{field} must be a number from 0 to 1")
    return number


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    try:
        data = json.loads(args.index.read_text(encoding="utf-8"))
        references = data.get("references", [])
        if not isinstance(references, list):
            raise ValueError("references must be an array")
        ranked: list[dict[str, Any]] = []
        for position, reference in enumerate(references):
            if not isinstance(reference, dict):
                raise ValueError(f"references[{position}] must be an object")
            reference_id = reference.get("reference_id")
            if not isinstance(reference_id, str) or not reference_id:
                raise ValueError(f"references[{position}].reference_id must be set")
            components = {
                name: bounded(reference.get(name, 0), f"{reference_id}.{name}")
                for name in WEIGHTS
            }
            score = round(sum(components[name] * WEIGHTS[name] for name in WEIGHTS) * 100, 2)
            ranked.append({**reference, "score_components": components, "reference_score": score})
        ranked.sort(key=lambda item: (-item["reference_score"], item["reference_id"]))
        output = {
            "schema_version": "1.0",
            "campaign_id": data.get("campaign_id"),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "weights": WEIGHTS,
            "selected_reference_id": ranked[0]["reference_id"] if ranked else None,
            "references": ranked,
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
    raise SystemExit(main())
