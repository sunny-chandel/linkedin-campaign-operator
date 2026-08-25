#!/usr/bin/env python3
"""Append one evidence record to an adaptive scheduling model."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VALID_MODELS = {
    "publication_timing",
    "response_latency",
    "regional_opportunity",
    "concentration",
    "candidate_staleness",
}
REQUIRED_FIELDS = {"context", "prediction", "decision", "confidence", "next_measurement_trigger"}


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", type=Path, help="working-algorithm-model.json")
    parser.add_argument("model_name", choices=sorted(VALID_MODELS))
    parser.add_argument("observation", type=Path, help="JSON observation")
    parser.add_argument("--now")
    args = parser.parse_args()
    try:
        model = json.loads(args.model.read_text(encoding="utf-8"))
        observation = json.loads(args.observation.read_text(encoding="utf-8"))
        if not isinstance(model, dict) or not isinstance(observation, dict):
            raise ValueError("model and observation must contain JSON objects")
        missing = sorted(field for field in REQUIRED_FIELDS if not observation.get(field))
        if missing:
            raise ValueError(f"observation missing required fields: {', '.join(missing)}")
        confidence = observation.get("confidence")
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            raise ValueError("confidence must be a number from 0 to 1")
        now = args.now or datetime.now(timezone.utc).isoformat()
        scheduling = model.setdefault("scheduling_models", {})
        target = scheduling.setdefault(args.model_name, {"observations": []})
        observations = target.setdefault("observations", [])
        if not isinstance(observations, list):
            raise ValueError(f"scheduling_models.{args.model_name}.observations must be an array")
        observations.append({**observation, "observed_at": observation.get("observed_at", now)})
        target["updated_at"] = now
        model["updated_at"] = now
        atomic_write(args.model, model)
        print(json.dumps({"valid": True, "model_name": args.model_name, "observation_count": len(observations)}, indent=2))
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
