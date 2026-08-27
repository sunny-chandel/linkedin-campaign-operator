#!/usr/bin/env python3
"""Maintain the six-package pipeline and verified rolling publication ledger."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


EXECUTION_SCRIPTS = Path(__file__).resolve().parents[2] / "linkedin-engagement-execution" / "scripts"
sys.path.insert(0, str(EXECUTION_SCRIPTS))
from rolling_output import POST_CAP, POST_TARGET, parse_time, refresh_output  # noqa: E402


ANALYTICS_OFFSETS = (30, 120, 360, 1440)
REQUIRED_PACKAGE_STAGES = (
    "research_brief",
    "claim_verification",
    "caption",
    "asset",
    "watermark",
    "validation",
    "publication_decision",
)


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain an object")
    return value


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


def validated_packages(pipeline: dict[str, Any], now: datetime) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in pipeline.get("packages", []):
        if not isinstance(item, dict) or item.get("status") not in {"validated", "ready"}:
            continue
        expires = parse_time(item.get("freshness_expiry"))
        if expires is not None and expires <= now:
            item["status"] = "stale-replacement-required"
            item["replacement_required"] = True
            continue
        stages = item.get("stages", {})
        if not isinstance(stages, dict) or not all(stages.get(stage) is True for stage in REQUIRED_PACKAGE_STAGES):
            continue
        result.append(item)
    return result


def portfolio_errors(packages: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    if len(packages) < 6:
        errors.append("six validated unpublished packages are required")
        return errors
    sample = packages[:6]
    regions = [str(item.get("region") or "") for item in sample]
    if "india" not in regions or not any(region in {"us", "us-central"} for region in regions):
        errors.append("portfolio must retain at least one India and one US post")
    pillars = {str(item.get("content_pillar") or "") for item in sample}
    formats = {str(item.get("format_treatment") or "") for item in sample}
    if len(pillars - {""}) < 4:
        errors.append("portfolio requires at least four content pillars")
    if len(formats - {""}) < 3:
        errors.append("portfolio requires at least three format treatments")
    for previous, current in zip(sample, sample[1:]):
        for field in ("topic", "angle", "format_treatment"):
            if previous.get(field) and previous.get(field) == current.get(field):
                errors.append(f"consecutive packages repeat {field}")
    return sorted(set(errors))


def evaluate(state_dir: Path, now: datetime, *, record: bool) -> dict[str, Any]:
    path = state_dir / "content-pipeline.json"
    pipeline = load_object(path)
    ready = validated_packages(pipeline, now)
    errors = portfolio_errors(ready) if len(ready) >= 6 else ["six validated unpublished packages are required"]
    output = refresh_output(state_dir, now, write=record)
    result = {
        "valid": True,
        "evaluated_at": now.isoformat(),
        "topic_candidates": len(pipeline.get("topic_candidates", [])),
        "briefs": len(pipeline.get("briefs", [])),
        "validated_unpublished_packages": len(ready),
        "inventory_target": 6,
        "inventory_debt": max(0, 6 - len(ready)),
        "portfolio_errors": errors,
        "rolling_output": output["publishing"],
        "next_task": "six-package-replenishment" if len(ready) < 6 or errors else "publication-execution",
    }
    pipeline["schema_version"] = "2.0"
    pipeline["inventory"] = {
        "validated_unpublished": len(ready),
        "target": 6,
        "debt": max(0, 6 - len(ready)),
        "evaluated_at": now.isoformat(),
    }
    pipeline["replacement_requirements"] = [
        item.get("package_id") for item in pipeline.get("packages", [])
        if isinstance(item, dict) and item.get("replacement_required") is True
    ]
    if record:
        atomic_write(path, pipeline)
    return result


def record_publication_evidence(
    state_dir: Path,
    evidence: dict[str, Any],
    now: datetime,
) -> dict[str, Any]:
    if evidence.get("verified") is not True:
        raise ValueError("publication evidence must be verified")
    post_id = evidence.get("post_id") or evidence.get("post_url")
    if not post_id:
        raise ValueError("publication evidence needs post_id or post_url")
    published_at = parse_time(evidence.get("published_at")) or now
    if published_at > now:
        raise ValueError("published_at cannot be in the future")
    output = refresh_output(state_dir, now, write=False)
    if int(output["publishing"]["rolling_24h_posts"]) >= POST_CAP:
        raise ValueError("rolling 24-hour publication cap is exhausted")
    existing = []
    evidence_log = state_dir / "publication-evidence.jsonl"
    if evidence_log.is_file():
        existing = [json.loads(line) for line in evidence_log.read_text(encoding="utf-8").splitlines() if line.strip()]
    if any((item.get("post_id") or item.get("post_url")) == post_id for item in existing if isinstance(item, dict)):
        raise ValueError(f"publication already recorded: {post_id}")
    prior_times = [
        parse_time(item.get("published_at")) for item in existing
        if isinstance(item, dict) and item.get("verified") is True
    ]
    prior_times = [value for value in prior_times if value is not None and value <= now]
    if prior_times and (published_at - max(prior_times)).total_seconds() < 120 * 60:
        raise ValueError("absolute 120-minute publication spacing floor is not satisfied")
    record = {
        **evidence,
        "schema_version": "2.0",
        "published_at": published_at.isoformat(),
        "verified_at": evidence.get("verified_at") or now.isoformat(),
    }
    with evidence_log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    pipeline_path = state_dir / "content-pipeline.json"
    pipeline = load_object(pipeline_path)
    for package in pipeline.get("packages", []):
        if isinstance(package, dict) and package.get("package_id") == evidence.get("package_id"):
            package["status"] = "published"
            package["post_id"] = post_id
            package["published_at"] = record["published_at"]
            package["publication_evidence"] = str(post_id)
            package["stages"] = {**package.get("stages", {}), "live_verification": True}
    pipeline.setdefault("analytics_schedule", []).extend(
        {
            "post_id": post_id,
            "checkpoint_minutes": minutes,
            "due_at": (published_at + timedelta(minutes=minutes)).isoformat(),
            "status": "pending",
            "required_artifacts": ["snapshot", "learning", "decision", "next_measurement_trigger"],
        }
        for minutes in ANALYTICS_OFFSETS
    )
    atomic_write(pipeline_path, pipeline)
    after = refresh_output(state_dir, now, write=True)
    return {
        "valid": True,
        "post_id": post_id,
        "rolling_24h_posts": after["publishing"]["rolling_24h_posts"],
        "target": POST_TARGET,
        "cap": POST_CAP,
        "post_debt": after["publishing"]["debt"],
        "analytics_checkpoints_minutes": list(ANALYTICS_OFFSETS),
        "replenishment_required": True,
    }


def record_publication(state_dir: Path, evidence_path: Path, now: datetime) -> dict[str, Any]:
    return record_publication_evidence(state_dir, load_object(evidence_path), now)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state_dir", type=Path)
    parser.add_argument("--now")
    parser.add_argument("--record", action="store_true")
    parser.add_argument("--record-publication", type=Path)
    args = parser.parse_args()
    now = parse_time(args.now) if args.now else datetime.now(timezone.utc)
    if now is None:
        parser.error("--now must be an ISO timestamp")
    try:
        state_dir = args.state_dir.expanduser().resolve()
        result = record_publication(state_dir, args.record_publication, now) if args.record_publication else evaluate(state_dir, now, record=args.record)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
