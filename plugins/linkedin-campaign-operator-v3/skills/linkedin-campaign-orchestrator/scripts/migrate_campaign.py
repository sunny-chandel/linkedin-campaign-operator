#!/usr/bin/env python3
"""Add current safe defaults and artifacts to an existing campaign directory."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any


def merge_missing(current: Any, defaults: Any) -> tuple[Any, bool]:
    if not isinstance(current, dict) or not isinstance(defaults, dict):
        return current, False
    changed = False
    merged = dict(current)
    for key, default_value in defaults.items():
        if key not in merged:
            merged[key] = default_value
            changed = True
        elif isinstance(merged[key], dict) and isinstance(default_value, dict):
            merged_value, nested_changed = merge_missing(merged[key], default_value)
            merged[key] = merged_value
            changed = changed or nested_changed
    return merged, changed


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
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


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state_dir", type=Path)
    args = parser.parse_args()

    state_dir = args.state_dir.expanduser().resolve()
    config_path = state_dir / "campaign-config.json"
    if not config_path.is_file():
        parser.error(f"missing existing campaign configuration: {config_path}")

    assets_dir = Path(__file__).resolve().parent.parent / "assets"
    defaults = load_object(assets_dir / "campaign-config.template.json")
    config = load_object(config_path)
    campaign_id = config.get("campaign_id")
    if not isinstance(campaign_id, str) or not campaign_id:
        parser.error("campaign-config.json requires a campaign_id before migration")

    merged, changed = merge_missing(config, defaults)
    if changed:
        atomic_write_json(config_path, merged)

    state_path = state_dir / "campaign-state.json"
    state_updated = False
    if state_path.is_file():
        state_defaults = load_object(assets_dir / "campaign-state.template.json")
        state = load_object(state_path)
        merged_state, state_updated = merge_missing(state, state_defaults)
        if state_updated:
            atomic_write_json(state_path, merged_state)

    created: list[str] = []
    artifacts = {
        "subscription-inventory.json": {
            "schema_version": "1.0",
            "campaign_id": campaign_id,
            "generated_at": None,
            "subscription": {},
            "features": [],
        },
        "subscription-utilization-plan.json": {
            "schema_version": "1.0",
            "campaign_id": campaign_id,
            "generated_at": None,
            "features": [],
            "summary": {},
        },
    }
    for name, initial in artifacts.items():
        path = state_dir / name
        if not path.exists():
            atomic_write_json(path, initial)
            created.append(name)
    results = state_dir / "subscription-results.jsonl"
    if not results.exists():
        results.touch()
        created.append(results.name)

    print(
        json.dumps(
            {
                "migrated": str(state_dir),
                "config_updated": changed,
                "state_updated": state_updated,
                "created": created,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
