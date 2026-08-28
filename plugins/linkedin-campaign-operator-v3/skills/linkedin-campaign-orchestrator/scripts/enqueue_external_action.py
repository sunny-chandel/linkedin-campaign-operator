#!/usr/bin/env python3
"""Atomically enqueue only canonical, leased LinkedIn actions for the daemon."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping

from automation_readiness import normalize_action_class, task_readiness
from execute_external_action import request_parts


OUTBOX_STATUSES = ("pending", "running", "verified", "deferred", "ambiguous", "failed")


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def atomic_write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(dict(value), handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def find_task(queue: Mapping[str, Any], task_id: str) -> dict[str, Any]:
    for item in queue.get("items", []):
        if isinstance(item, dict) and item.get("task_id") == task_id:
            return item
    raise ValueError(f"unknown task_id: {task_id}")


def publication_action(state_dir: Path, task: Mapping[str, Any]) -> dict[str, Any]:
    package_id = task.get("package_id")
    if not isinstance(package_id, str) or not package_id:
        raise ValueError("publication task requires package_id")
    pipeline = load_object(state_dir / "content-pipeline.json")
    package = next(
        (
            item
            for item in pipeline.get("packages", [])
            if isinstance(item, dict) and item.get("package_id") == package_id
        ),
        None,
    )
    if package is None:
        raise ValueError(f"unknown publication package: {package_id}")
    decision = package.get("publication_decision", {})
    if not isinstance(decision, Mapping) or decision.get("decision") != "publish-now":
        raise ValueError("publication package is not in publish-now state")
    score = decision.get("opportunity_score")
    if isinstance(score, bool) or not isinstance(score, (int, float)) or score < 65:
        raise ValueError("publication package opportunity score is below 65")
    source_path = package.get("source_path")
    asset_path = package.get("asset_path")
    if not isinstance(source_path, str) or not isinstance(asset_path, str):
        raise ValueError("publication package requires source_path and asset_path")
    draft = load_object((state_dir / source_path).resolve())
    caption = draft.get("caption")
    if not isinstance(caption, str) or not caption.strip():
        raise ValueError("validated publication package has no caption")
    media_path = (state_dir / asset_path).resolve()
    if not media_path.is_file():
        raise ValueError(f"publication asset is missing: {asset_path}")
    return {
        "action_class": "publication",
        "text": caption,
        "media_file": str(media_path),
        "alt_text": str(package.get("topic") or draft.get("topic") or "LinkedIn post image"),
        "package_id": package_id,
        "region": task.get("region") or package.get("region"),
        "opportunity_score": float(score),
    }


def canonical_actions(state_dir: Path, task: Mapping[str, Any]) -> list[dict[str, Any]]:
    task_type = str(task.get("task_type") or "")
    if task_type in {"publication-execution", "publication-opportunity"}:
        return [publication_action(state_dir, task)]
    raw_actions = task.get("actions")
    if isinstance(raw_actions, list) and raw_actions:
        return [dict(action) for action in raw_actions if isinstance(action, Mapping)]
    action_class = normalize_action_class(task.get("action_class") or task.get("action_type"))
    return [dict(task)] if action_class else []


def normalize_action(
    task: Mapping[str, Any],
    action: Mapping[str, Any],
    position: int,
    total: int,
) -> dict[str, Any]:
    action_class = normalize_action_class(action.get("action_class") or action.get("action_type"))
    if not action_class:
        raise ValueError("canonical action has no supported action class")
    text = (
        action.get("text")
        or action.get("exact_text")
        or action.get("commentary")
        or action.get("draft_text")
    )
    base_key = str(task.get("idempotency_key") or task.get("task_id"))
    candidate_id = action.get("candidate_id") or action.get("opportunity_id")
    suffix = str(candidate_id) if candidate_id else str(position)
    result = dict(action)
    result.update(
        {
            "action_class": action_class,
            "text": text,
            "source_task_id": task.get("task_id"),
            "source_lease_id": task.get("lease_id"),
            "candidate_id": candidate_id,
            "group_expected": total,
            "idempotency_key": str(action.get("idempotency_key") or f"{base_key}:{suffix}"),
        }
    )
    return result


def existing_path(outbox: Path, filename: str) -> Path | None:
    for status in OUTBOX_STATUSES:
        candidate = outbox / status / filename
        if candidate.exists():
            return candidate
    return None


def enqueue_task(state_dir: Path, task_id: str) -> dict[str, Any]:
    queue = load_object(state_dir / "work-queue.json")
    executor = load_object(state_dir / "external-executor.json")
    task = find_task(queue, task_id)
    if task.get("status") not in {"leased", "running"}:
        raise ValueError(f"task must be leased or running before enqueue, got {task.get('status')}")
    if not isinstance(task.get("lease_id"), str) or not task.get("lease_id"):
        raise ValueError("external task requires an active lease_id")
    readiness = task_readiness(task, executor)
    if not readiness["zero_human_ready"]:
        return {"valid": False, "readiness": readiness, "enqueued": []}
    actions = canonical_actions(state_dir, task)
    if not actions:
        raise ValueError("leased external task contains no canonical actions")
    actor_urn = executor.get("verification", {}).get("verified_actor_urn")
    if not isinstance(actor_urn, str) or not actor_urn.startswith("urn:li:person:"):
        raise ValueError("executor does not contain a verified actor URN")
    outbox = state_dir / "external-action-outbox"
    for status in OUTBOX_STATUSES:
        (outbox / status).mkdir(parents=True, exist_ok=True)
    enqueued: list[str] = []
    existing: list[str] = []
    for position, raw in enumerate(actions, start=1):
        action = normalize_action(task, raw, position, len(actions))
        request_parts(action, actor_urn)
        filename = hashlib.sha256(action["idempotency_key"].encode("utf-8")).hexdigest() + ".json"
        prior = existing_path(outbox, filename)
        if prior:
            existing.append(str(prior.relative_to(state_dir)))
            continue
        destination = outbox / "pending" / filename
        atomic_write(destination, action)
        enqueued.append(str(destination.relative_to(state_dir)))
    return {
        "valid": True,
        "decision": "queued-for-autonomous-daemon",
        "task_id": task_id,
        "lease_id": task.get("lease_id"),
        "enqueued": enqueued,
        "already_present": existing,
        "owner_input_required": False,
        "observer_input_required": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state_dir", type=Path)
    parser.add_argument("--task-id", required=True)
    args = parser.parse_args()
    try:
        result = enqueue_task(args.state_dir.expanduser().resolve(), args.task_id)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result["valid"] else 2
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
