#!/usr/bin/env python3
"""Validate and append one runtime-learning record to a JSONL ledger."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


STATUSES = {
    "observed", "hypothesis", "testing", "provisionally-supported", "validated",
    "contradicted", "rolled-back", "expired", "archived",
}
CONFIDENCE = {"confirmed", "high", "moderate", "speculative"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", type=Path)
    parser.add_argument("record", type=Path, help="JSON file containing one learning record")
    args = parser.parse_args()

    try:
        record = json.loads(args.record.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    if not isinstance(record, dict):
        parser.error("record must be a JSON object")

    for field in ("learning_id", "claim", "source_url", "source_tier", "confidence", "status"):
        if record.get(field) in (None, ""):
            parser.error(f"missing required field: {field}")
    if record["status"] not in STATUSES:
        parser.error(f"invalid status: {record['status']}")
    if record["confidence"] not in CONFIDENCE:
        parser.error(f"invalid confidence: {record['confidence']}")
    if record.get("changes_fixed_rule") is True:
        parser.error("runtime learning cannot change a fixed rule")

    record.setdefault("recorded_at", datetime.now(timezone.utc).isoformat())
    args.ledger.parent.mkdir(parents=True, exist_ok=True)
    with args.ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(json.dumps({"appended": record["learning_id"], "ledger": str(args.ledger)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
