#!/usr/bin/env python3
"""Atomically upsert discovered engagement opportunities into the canonical queue."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ORCHESTRATOR_SCRIPTS = Path(__file__).resolve().parents[2] / "linkedin-campaign-orchestrator" / "scripts"
sys.path.insert(0, str(ORCHESTRATOR_SCRIPTS))
from opportunity_recovery import eligible_opportunities  # noqa: E402


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain an object")
    return value


def parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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


def identity(record: dict[str, Any]) -> str:
    explicit = record.get("opportunity_id") or record.get("candidate_id")
    if isinstance(explicit, str) and explicit:
        return explicit
    candidate = record.get("candidate_identity") or record.get("target_id")
    post = record.get("post_id") or record.get("post_url")
    action = record.get("action_type")
    if not candidate or not action:
        raise ValueError("each opportunity needs an id or candidate identity plus action type")
    return f"{candidate}:{post or 'relationship'}:{action}"


def eligible_count(document: dict[str, Any], now: datetime) -> int:
    count = 0
    for item in document.get("opportunities", []):
        if not isinstance(item, dict) or item.get("status") not in {"qualified", "ready"}:
            continue
        expires = parse_time(item.get("expires_at") or item.get("expiry"))
        not_before = parse_time(item.get("not_before"))
        if expires is not None and expires <= now:
            continue
        if not_before is not None and not_before > now:
            continue
        if item.get("action_available", True) is True:
            count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state_dir", type=Path)
    parser.add_argument("discoveries", type=Path, help="JSON object with source and opportunities")
    parser.add_argument("--now")
    args = parser.parse_args()
    state_dir = args.state_dir.expanduser().resolve()
    now = parse_time(args.now) if args.now else datetime.now(timezone.utc)
    if now is None:
        parser.error("--now must be an ISO timestamp")
    try:
        incoming = load_object(args.discoveries)
        source = incoming.get("source")
        records = incoming.get("opportunities")
        if not isinstance(source, str) or not source or not isinstance(records, list):
            raise ValueError("discoveries must contain source and an opportunities array")
        queue_path = state_dir / "engagement-opportunities.json"
        document = load_object(queue_path) if queue_path.is_file() else {
            "schema_version": "2.0",
            "campaign_id": incoming.get("campaign_id"),
            "opportunities": [],
        }
        current = document.setdefault("opportunities", [])
        if not isinstance(current, list):
            raise ValueError("canonical opportunities must be an array")
        by_id = {identity(item): item for item in current if isinstance(item, dict)}
        accepted = 0
        rejected = 0
        for raw in records:
            if not isinstance(raw, dict):
                rejected += 1
                continue
            item = dict(raw)
            item_id = identity(item)
            item.update(
                {
                    "opportunity_id": item_id,
                    "candidate_id": item.get("candidate_id") or item_id,
                    "source": source,
                    "discovered_at": item.get("discovered_at") or now.isoformat(),
                    "updated_at": now.isoformat(),
                    "status": item.get("status") or "qualified",
                    "expires_at": item.get("expires_at")
                    or (now + timedelta(hours=int(item.get("freshness_hours", 24) or 24))).isoformat(),
                    "evidence": item.get("evidence") or {},
                }
            )
            prior = by_id.get(item_id)
            if prior is not None and prior.get("status") in {"executed", "expired", "rejected"}:
                rejected += 1
                continue
            if prior is None:
                current.append(item)
                by_id[item_id] = item
            else:
                prior.update(item)
            accepted += 1
        for item in current:
            if not isinstance(item, dict) or item.get("status") not in {"qualified", "ready"}:
                continue
            expires = parse_time(item.get("expires_at") or item.get("expiry"))
            if expires is not None and expires <= now:
                item["status"] = "expired"
                item["expired_at"] = now.isoformat()
        state_path = state_dir / "campaign-state.json"
        state = load_object(state_path)
        config = load_object(state_dir / "campaign-config.json")
        document["schema_version"] = "2.0"
        document["updated_at"] = now.isoformat()
        document["eligible_count"] = len(eligible_opportunities(document, state, config, now))
        document["count_source"] = "canonical-records"
        atomic_write(queue_path, document)

        recovery = state.setdefault("opportunity_recovery", {})
        history = recovery.setdefault("source_performance", {})
        performance = history.setdefault(source, {})
        performance["attempts"] = int(performance.get("attempts", 0) or 0) + 1
        performance["accepted_candidates"] = int(performance.get("accepted_candidates", 0) or 0) + accepted
        performance["rejected_candidates"] = int(performance.get("rejected_candidates", 0) or 0) + rejected
        performance["last_yield"] = accepted / max(1, len(records))
        performance["last_attempt_at"] = now.isoformat()
        if accepted == 0:
            performance["backoff_until"] = (now + timedelta(minutes=30)).isoformat()
        recovery["last_discovery_source"] = source
        reserve = state.setdefault("engagement_scaling", {}).setdefault("adaptive_reserve", {})
        reserve["qualified_count"] = document["eligible_count"]
        reserve["count_source"] = "engagement-opportunities.json"
        state["updated_at"] = now.isoformat()
        atomic_write(state_path, state)
        print(json.dumps({
            "valid": True,
            "source": source,
            "accepted": accepted,
            "rejected": rejected,
            "canonical_eligible_count": document["eligible_count"],
            "backoff_until": performance.get("backoff_until"),
        }, indent=2))
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
