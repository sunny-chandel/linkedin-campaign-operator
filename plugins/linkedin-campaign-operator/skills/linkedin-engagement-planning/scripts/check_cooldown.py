#!/usr/bin/env python3
"""Check whether a proactive interaction is allowed under campaign cooldowns."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


def parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("interaction_log", type=Path)
    parser.add_argument("person_id")
    parser.add_argument("--now", help="ISO-8601 timestamp; defaults to current UTC")
    args = parser.parse_args()

    now = parse_time(args.now) if args.now else datetime.now(timezone.utc)
    events: list[dict] = []
    try:
        lines = args.interaction_log.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        lines = []

    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            parser.error(f"invalid JSON on line {number}: {exc}")
        if event.get("person_id") == args.person_id and event.get("proactive") is True:
            event["_time"] = parse_time(event["occurred_at"])
            events.append(event)

    in_72h = [e for e in events if e["_time"] > now - timedelta(hours=72)]
    in_7d = [e for e in events if e["_time"] > now - timedelta(days=7)]
    allowed = len(in_72h) == 0 and len(in_7d) < 2
    next_allowed = now
    if in_72h:
        next_allowed = max(e["_time"] + timedelta(hours=72) for e in in_72h)
    if len(in_7d) >= 2:
        next_allowed = max(next_allowed, sorted(e["_time"] for e in in_7d)[-2] + timedelta(days=7))

    print(json.dumps({
        "person_id": args.person_id,
        "allowed": allowed,
        "proactive_actions_last_72h": len(in_72h),
        "proactive_actions_last_7d": len(in_7d),
        "next_allowed_at": next_allowed.isoformat(),
    }, indent=2))
    return 0 if allowed else 2


if __name__ == "__main__":
    sys.exit(main())
