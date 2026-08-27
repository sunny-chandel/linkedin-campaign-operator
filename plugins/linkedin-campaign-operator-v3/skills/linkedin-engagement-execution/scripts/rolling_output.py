#!/usr/bin/env python3
"""Calculate canonical rolling-24-hour action and publication output."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ACTION_TARGET = 160
ACTION_CAP = 200
POST_TARGET = 6
POST_CAP = 8
ACTION_CHECKPOINTS = (40, 80, 120, 160)
WINDOW_HOURS = 24
DIRECT_LANE = "direct-inbound"


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


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            records.append(value)
    return records


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


def _record_time(record: dict[str, Any], keys: tuple[str, ...]) -> datetime | None:
    for key in keys:
        parsed = parse_time(record.get(key))
        if parsed is not None:
            return parsed
    return None


def calculate_output(state_dir: Path, now: datetime) -> dict[str, Any]:
    now = now.astimezone(timezone.utc)
    window_start = now - timedelta(hours=WINDOW_HOURS)
    campaign_id = None
    state_path = state_dir / "campaign-state.json"
    if state_path.is_file():
        state_value = json.loads(state_path.read_text(encoding="utf-8"))
        if isinstance(state_value, dict):
            campaign_id = state_value.get("campaign_id")
    action_records = []
    direct_records = []
    seen_actions: set[str] = set()
    for record in read_jsonl(state_dir / "interaction-log.jsonl"):
        occurred = _record_time(record, ("executed_at", "recorded_at", "timestamp", "created_at"))
        if occurred is None or not window_start < occurred <= now:
            continue
        if record.get("confirmed") is False or record.get("external_action_occurred") is False:
            continue
        action_id = str(record.get("action_id") or "")
        if action_id and action_id in seen_actions:
            continue
        if action_id:
            seen_actions.add(action_id)
        if record.get("lane") == DIRECT_LANE:
            direct_records.append(record)
        else:
            action_records.append(record)

    publication_records = []
    seen_publications: set[str] = set()
    for record in read_jsonl(state_dir / "publication-evidence.jsonl"):
        occurred = _record_time(record, ("published_at", "verified_at", "recorded_at", "timestamp"))
        if occurred is None or not window_start < occurred <= now or record.get("verified") is not True:
            continue
        identity = str(record.get("post_id") or record.get("post_url") or record.get("idempotency_key") or "")
        if not identity or identity in seen_publications:
            continue
        seen_publications.add(identity)
        publication_records.append(record)

    actions = len(action_records)
    posts = len(publication_records)
    result = {
        "schema_version": "2.0",
        "calculated_at": now.isoformat(),
        "window": {
            "hours": WINDOW_HOURS,
            "start_at": window_start.isoformat(),
            "end_at": now.isoformat(),
        },
        "actions": {
            "rolling_24h_actions": actions,
            "target": ACTION_TARGET,
            "hard_cap": ACTION_CAP,
            "debt": max(0, ACTION_TARGET - actions),
            "remaining_capacity": max(0, ACTION_CAP - actions),
            "target_met": actions >= ACTION_TARGET,
            "cap_reached": actions >= ACTION_CAP,
            "checkpoints": list(ACTION_CHECKPOINTS),
            "checkpoints_reached": [checkpoint for checkpoint in ACTION_CHECKPOINTS if actions >= checkpoint],
            "direct_inbound_replies": len(direct_records),
            "direct_inbound_outside_cap": True,
            "evidence_file": "interaction-log.jsonl",
        },
        "publishing": {
            "rolling_24h_posts": posts,
            "target": POST_TARGET,
            "hard_cap": POST_CAP,
            "debt": max(0, POST_TARGET - posts),
            "remaining_capacity": max(0, POST_CAP - posts),
            "target_met": posts >= POST_TARGET,
            "cap_reached": posts >= POST_CAP,
            "verified_post_ids": sorted(seen_publications),
            "evidence_file": "publication-evidence.jsonl",
        },
        "campaign_id": campaign_id,
        "availability": {
            "action_evidence_available": (state_dir / "interaction-log.jsonl").is_file(),
            "publication_evidence_available": (state_dir / "publication-evidence.jsonl").is_file(),
        },
    }
    return result


def sync_legacy_state(state_dir: Path, output: dict[str, Any]) -> None:
    state_path = state_dir / "campaign-state.json"
    if not state_path.is_file():
        return
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if not isinstance(state, dict):
        raise ValueError("campaign-state.json must contain an object")
    actions = output["actions"]
    publishing = output["publishing"]
    scaling = state.setdefault("engagement_scaling", {})
    scaling.update(
        {
            "rolling_24h_actions": actions["rolling_24h_actions"],
            "rolling_action_target": ACTION_TARGET,
            "rolling_action_cap": ACTION_CAP,
            "action_debt": actions["debt"],
            "base_actions_used": actions["rolling_24h_actions"],
            "base_daily_ceiling": ACTION_CAP,
            "direct_reply_overage": actions["direct_inbound_replies"],
        }
    )
    publishing_state = state.setdefault("publishing", {})
    publishing_state.update(
        {
            "rolling_24h_posts": publishing["rolling_24h_posts"],
            "rolling_post_target": POST_TARGET,
            "rolling_post_cap": POST_CAP,
            "post_debt": publishing["debt"],
            "posts_published": publishing["rolling_24h_posts"],
        }
    )
    state["operational_output"] = {
        "path": "operational-output.json",
        "last_calculated_at": output["calculated_at"],
    }
    state["updated_at"] = output["calculated_at"]
    atomic_write(state_path, state)


def refresh_output(state_dir: Path, now: datetime, *, write: bool = True) -> dict[str, Any]:
    result = calculate_output(state_dir, now)
    if write:
        atomic_write(state_dir / "operational-output.json", result)
        sync_legacy_state(state_dir, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state_dir", type=Path)
    parser.add_argument("--now")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()
    now = parse_time(args.now) if args.now else datetime.now(timezone.utc)
    if now is None:
        parser.error("--now must be an ISO timestamp")
    try:
        result = refresh_output(args.state_dir.expanduser().resolve(), now, write=not args.no_write)
        print(json.dumps({"valid": True, **result}, indent=2, ensure_ascii=False))
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
