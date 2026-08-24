#!/usr/bin/env python3
"""Compute normalized campaign metrics from a JSON post snapshot."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ENGAGEMENT_FIELDS = ("reactions", "comments", "saves", "sends", "reposts")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path, help="JSON object containing impressions and engagement fields")
    args = parser.parse_args()

    try:
        data = json.loads(args.snapshot.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        parser.error(str(exc))

    impressions = data.get("impressions")
    if not isinstance(impressions, (int, float)) or impressions < 0:
        parser.error("impressions must be a non-negative number")
    values = {}
    for field in ENGAGEMENT_FIELDS:
        value = data.get(field, 0)
        if not isinstance(value, (int, float)) or value < 0:
            parser.error(f"{field} must be a non-negative number")
        values[field] = value

    engagements = sum(values.values())
    output = dict(data)
    output["calculated_engagements"] = engagements
    output["engagement_rate"] = round(engagements / impressions, 6) if impressions else None
    members_reached = data.get("members_reached")
    if isinstance(members_reached, (int, float)) and members_reached > 0:
        output["engagements_per_member_reached"] = round(engagements / members_reached, 6)
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
