#!/usr/bin/env python3
"""Record one confirmed action against the canonical rolling-24-hour contract."""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXECUTION_SCRIPTS = Path(__file__).resolve().parents[2] / "linkedin-engagement-execution" / "scripts"
sys.path.insert(0, str(EXECUTION_SCRIPTS))
from rolling_output import ACTION_CAP, ACTION_TARGET, atomic_write, parse_time, refresh_output  # noqa: E402


VALID_LANES = {"proactive", "soft-reciprocity", "direct-inbound"}


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


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
        log_path = state_dir / "interaction-log.jsonl"
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
        action_type = str(action.get("action_type") or "").lower()
        if action_type in {"dm", "message", "direct-message"} and lane != "direct-inbound":
            if action.get("connection_status") not in {"existing", "connected"}:
                raise ValueError("proactive DMs require an existing connection")
            prior_evidence = action.get("prior_interaction_evidence")
            if prior_evidence is not True and not isinstance(prior_evidence, dict):
                raise ValueError("proactive DMs require prior interaction evidence")

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

        now_value = parse_time(args.now) if args.now else datetime.now(timezone.utc)
        if now_value is None:
            raise ValueError("--now must be an ISO timestamp")
        before = refresh_output(state_dir, now_value, write=False)
        rolling_actions = int(before["actions"]["rolling_24h_actions"])
        if lane != "direct-inbound" and rolling_actions >= ACTION_CAP:
            raise ValueError("rolling 24-hour action cap is exhausted")
        budget_class = "direct-inbound-outside-cap" if lane == "direct-inbound" else "rolling-base"

        record = {
            **action,
            "schema_version": "2.0",
            "recorded_at": now_value.isoformat(),
            "confirmed": True,
            "external_action_occurred": True,
            "budget_class": budget_class,
        }
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        output = refresh_output(state_dir, now_value, write=True)
        state_path = state_dir / "campaign-state.json"
        state = load_object(state_path)
        state["last_confirmed_action"] = f"external-action:{action_id}"
        state["last_confirmed_action_at"] = now_value.isoformat()
        atomic_write(state_path, state)
        action_output = output["actions"]
        print(
            json.dumps(
                {
                    "valid": True,
                    "action_id": action_id,
                    "lane": lane,
                    "budget_class": budget_class,
                    "rolling_24h_actions": action_output["rolling_24h_actions"],
                    "rolling_action_target": ACTION_TARGET,
                    "rolling_action_cap": ACTION_CAP,
                    "action_debt": action_output["debt"],
                    "direct_inbound_replies": action_output["direct_inbound_replies"],
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
