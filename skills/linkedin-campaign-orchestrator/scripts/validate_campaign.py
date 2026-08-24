#!/usr/bin/env python3
"""Validate the minimum campaign configuration, consent, and state invariants."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REQUIRED_FILES = ("campaign-config.json", "consent-record.json", "campaign-state.json")
VALID_STATES = {"ready", "running", "recovering", "hard-blocked", "completed", "user-stopped"}


def load_json(path: Path, errors: list[str]) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"missing file: {path.name}")
        return {}
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON in {path.name}: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{path.name} must contain a JSON object")
        return {}
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state_dir", type=Path)
    parser.add_argument("--allow-draft", action="store_true", help="validate structure before activation")
    args = parser.parse_args()

    state_dir = args.state_dir.expanduser().resolve()
    errors: list[str] = []
    docs = {name: load_json(state_dir / name, errors) for name in REQUIRED_FILES}
    config = docs["campaign-config.json"]
    consent = docs["consent-record.json"]
    state = docs["campaign-state.json"]

    ids = {doc.get("campaign_id") for doc in docs.values() if doc}
    if not ids or None in ids or "replace-me" in ids:
        errors.append("campaign_id must be set in all required files")
    elif len(ids) != 1:
        errors.append(f"campaign_id mismatch: {sorted(ids)}")

    target = config.get("target", {})
    for key in ("name", "completion_formula", "required_evidence"):
        if target.get(key) in (None, "", []):
            errors.append(f"campaign-config.json target.{key} must be set")
    expected_metrics = {"metric_a": "followers", "metric_b": "connections"}
    for metric_key, expected_name in expected_metrics.items():
        metric = target.get(metric_key, {})
        if metric.get("name") != expected_name:
            errors.append(
                f"campaign-config.json target.{metric_key}.name must equal {expected_name}"
            )
        if isinstance(metric.get("baseline"), (int, float)) and metric["baseline"] < 0:
            errors.append(f"campaign-config.json target.{metric_key}.baseline must not be negative")
        if metric.get("goal") != 10000:
            errors.append(f"campaign-config.json target.{metric_key}.goal must equal 10000")

    owner = consent.get("owner", {})
    if owner.get("display_name") != "Sunny Chandel":
        errors.append("consent-record.json owner.display_name must equal Sunny Chandel")
    if owner.get("expected_linkedin_identity") != "Sunny Chandel":
        errors.append("consent-record.json owner.expected_linkedin_identity must equal Sunny Chandel")
    if consent.get("status") != "active" and not args.allow_draft:
        errors.append("consent-record.json status must be active")
    if not consent.get("activated_at") and not args.allow_draft:
        errors.append("consent-record.json activated_at must be set")
    accounts = consent.get("accounts", [])
    expected_url = "https://www.linkedin.com/in/sunny-chandel-6a05bb401/"
    if not any(account.get("url") == expected_url for account in accounts if isinstance(account, dict)):
        errors.append("consent-record.json accounts must contain Sunny's fixed LinkedIn profile URL")
    if not consent.get("approved_action_classes"):
        errors.append("consent-record.json approved_action_classes must be set")
    if not consent.get("data_directory"):
        errors.append("consent-record.json data_directory must be set")
    lifecycle = state.get("lifecycle_state")
    if lifecycle not in VALID_STATES:
        errors.append(f"campaign-state.json lifecycle_state must be one of {sorted(VALID_STATES)}")

    fixed = config.get("fixed_rules", {})
    expected = {
        "posts_per_day": 2,
        "windows_per_day": 4,
        "max_actions_per_window": 10,
        "new_target_min_followers": 3000,
        "cooldown_hours": 72,
        "max_proactive_actions_per_person_per_7d": 2,
    }
    for key, value in expected.items():
        if fixed.get(key) != value:
            errors.append(f"campaign-config.json fixed_rules.{key} must equal {value}")

    result = {"valid": not errors, "state_dir": str(state_dir), "errors": errors}
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
