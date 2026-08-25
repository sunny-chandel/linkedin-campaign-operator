#!/usr/bin/env python3
"""Record one executed action and update adaptive daily budget counters."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VALID_LANES = {"proactive", "soft-reciprocity", "direct-inbound"}


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def atomic_write(path: Path, value: dict[str, Any]) -> None:
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def relationship_strength(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("relationship_strength must be a number from 0 to 1")
    number = float(value)
    if not math.isfinite(number) or not 0 <= number <= 1:
        raise ValueError("relationship_strength must be a number from 0 to 1")
    return number


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state_dir", type=Path)
    parser.add_argument("action", type=Path, help="JSON action record")
    parser.add_argument("--now", help="ISO timestamp used in deterministic tests")
    args = parser.parse_args()

    state_dir = args.state_dir.expanduser().resolve()
    try:
        state_path = state_dir / "campaign-state.json"
        log_path = state_dir / "interaction-log.jsonl"
        state = load_object(state_path)
        action = load_object(args.action)
        action_id = action.get("action_id")
        if not isinstance(action_id, str) or not action_id.strip():
            raise ValueError("action_id must be set")
        lane = action.get("lane")
        if lane not in VALID_LANES:
            raise ValueError("lane must be proactive, soft-reciprocity, or direct-inbound")
        if not action.get("triggering_signal"):
            raise ValueError("triggering_signal must be set")
        if not isinstance(action.get("scheduling_rationale"), str) or not action["scheduling_rationale"].strip():
            raise ValueError("scheduling_rationale must be set")
        action["relationship_strength"] = relationship_strength(action.get("relationship_strength"))

        existing_ids: set[str] = set()
        if log_path.exists():
            for line in log_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                record = json.loads(line)
                if isinstance(record, dict) and isinstance(record.get("action_id"), str):
                    existing_ids.add(record["action_id"])
        if action_id in existing_ids:
            raise ValueError(f"action_id already recorded: {action_id}")

        scaling = state.setdefault("engagement_scaling", {})
        base_ceiling = int(scaling.get("base_daily_ceiling", 100))
        base_used = int(scaling.get("base_actions_used", 0))
        overage = int(scaling.get("direct_reply_overage", 0))
        if base_ceiling != 100 or not 0 <= base_used <= base_ceiling or overage < 0:
            raise ValueError("campaign state has invalid adaptive budget counters")
        if lane != "direct-inbound" and base_used >= base_ceiling:
            raise ValueError("shared base action ceiling is exhausted")
        if lane == "direct-inbound" and base_used >= base_ceiling:
            budget_class = "direct-reply-overage"
            overage += 1
        else:
            budget_class = "base"
            base_used += 1

        now = args.now or datetime.now(timezone.utc).isoformat()
        record = {
            **action,
            "schema_version": "1.1",
            "recorded_at": now,
            "budget_class": budget_class,
        }
        scaling["base_actions_used"] = base_used
        scaling["direct_reply_overage"] = overage
        state["last_confirmed_action"] = action_id
        state["updated_at"] = now
        atomic_write(state_path, state)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(
            json.dumps(
                {
                    "valid": True,
                    "action_id": action_id,
                    "lane": lane,
                    "budget_class": budget_class,
                    "base_actions_used": base_used,
                    "base_daily_ceiling": base_ceiling,
                    "direct_reply_overage": overage,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
