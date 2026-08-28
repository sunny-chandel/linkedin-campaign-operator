#!/usr/bin/env python3
"""Check whether a recurring campaign routine should run the campaign cycle now."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ACTIVE_TASK_STATES = {"leased", "running", "recovering", "missed-recovering"}


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain an object")
    return value


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state_dir", type=Path)
    parser.add_argument("--now", help="ISO timestamp used in deterministic tests")
    args = parser.parse_args()

    state_dir = args.state_dir.expanduser().resolve()
    now = parse_time(args.now) if args.now else datetime.now(timezone.utc)
    assert now is not None

    try:
        state = load_object(state_dir / "campaign-state.json")
        queue = load_object(state_dir / "work-queue.json")
        lifecycle = str(state.get("lifecycle_state") or "running")
        if lifecycle in {"completed", "stopped", "cancelled", "revoked"}:
            result = {
                "valid": True,
                "due": False,
                "action": "finish-no-change",
                "reason": "campaign-not-running",
                "lifecycle_state": lifecycle,
            }
        else:
            items = queue.get("items", [])
            if not isinstance(items, list):
                raise ValueError("work-queue.json items must be a list")
            active = [
                item for item in items
                if isinstance(item, dict) and item.get("status") in ACTIVE_TASK_STATES
            ]
            live = []
            expired = []
            for item in active:
                expiry = parse_time(item.get("lease_expires_at"))
                if expiry is not None and expiry <= now:
                    expired.append(str(item.get("task_id") or "unknown"))
                else:
                    live.append(str(item.get("task_id") or "unknown"))

            dispatcher = state.get("dispatcher", {})
            if not isinstance(dispatcher, dict):
                dispatcher = {}
            next_wake_at = dispatcher.get("next_wake_at")
            next_wake = parse_time(next_wake_at)
            if live:
                result = {
                    "valid": True,
                    "due": False,
                    "action": "finish-no-change",
                    "reason": "active-lease",
                    "active_task_ids": live,
                    "next_wake_at": next_wake_at,
                }
            elif expired:
                result = {
                    "valid": True,
                    "due": True,
                    "action": "run-campaign-cycle",
                    "reason": "expired-lease-recovery",
                    "expired_task_ids": expired,
                    "next_wake_at": next_wake_at,
                }
            elif next_wake is None:
                result = {
                    "valid": True,
                    "due": True,
                    "action": "run-campaign-cycle",
                    "reason": "missing-wake-recovery",
                    "next_wake_at": None,
                }
            elif now >= next_wake:
                result = {
                    "valid": True,
                    "due": True,
                    "action": "run-campaign-cycle",
                    "reason": "wake-due",
                    "next_wake_at": next_wake_at,
                }
            else:
                result = {
                    "valid": True,
                    "due": False,
                    "action": "finish-no-change",
                    "reason": "before-next-wake",
                    "next_wake_at": next_wake_at,
                    "seconds_until_wake": max(0, int((next_wake - now).total_seconds())),
                }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(
            json.dumps(
                {"valid": False, "due": False, "action": "inspect", "error": str(exc)},
                indent=2,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
