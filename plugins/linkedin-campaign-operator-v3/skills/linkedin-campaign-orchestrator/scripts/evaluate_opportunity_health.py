#!/usr/bin/env python3
"""Evaluate and optionally persist opportunity health and recovery tier."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from opportunity_recovery import evaluate_health
from runtime_state import append_jsonl, atomic_write, current_time, load_object


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state_dir", type=Path)
    parser.add_argument("--now", help="ISO timestamp used in deterministic tests")
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()
    state_dir = args.state_dir.expanduser().resolve()
    try:
        state = load_object(state_dir / "campaign-state.json")
        config = load_object(state_dir / "campaign-config.json")
        result = evaluate_health(state_dir, state, config, current_time(args.now))
        if args.record:
            atomic_write(state_dir / "campaign-state.json", state)
            append_jsonl(state_dir / "opportunity-health.jsonl", result)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
