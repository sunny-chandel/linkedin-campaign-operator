#!/usr/bin/env python3
"""Initialize mutable campaign state outside the installed plugin."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


TEMPLATES = {
    "campaign-config.template.json": "campaign-config.json",
    "consent-record.template.json": "consent-record.json",
    "campaign-state.template.json": "campaign-state.json",
}

DEFAULT_CAMPAIGN_ID = "sunny-linkedin-10k-10k"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state_dir", type=Path)
    parser.add_argument("--campaign-id", default=DEFAULT_CAMPAIGN_ID)
    parser.add_argument("--followers-baseline", type=int)
    parser.add_argument("--connections-baseline", type=int)
    parser.add_argument("--niche")
    args = parser.parse_args()

    state_dir = args.state_dir.expanduser().resolve()
    if state_dir.exists() and any(state_dir.iterdir()):
        parser.error(f"refusing to initialize non-empty directory: {state_dir}")

    assets_dir = Path(__file__).resolve().parent.parent / "assets"
    state_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()

    for template_name, output_name in TEMPLATES.items():
        source = assets_dir / template_name
        data = json.loads(source.read_text(encoding="utf-8"))
        data["campaign_id"] = args.campaign_id
        if output_name == "campaign-config.json":
            data["target"]["metric_a"]["baseline"] = args.followers_baseline
            data["target"]["metric_b"]["baseline"] = args.connections_baseline
            if args.niche:
                data["audience"]["niche"] = args.niche
        if output_name == "consent-record.json":
            data["data_directory"] = str(state_dir)
            data["activated_at"] = now
        if output_name == "campaign-state.json":
            data["updated_at"] = now
        (state_dir / output_name).write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    for name, initial in {
        "brand-profile.json": {
            "schema_version": "1.0",
            "campaign_id": args.campaign_id,
            "profile": {},
            "custom_overrides": {},
            "identity_hash": None,
            "generated_at": None,
        },
        "watermark-manifest.json": {
            "schema_version": "1.0",
            "campaign_id": args.campaign_id,
            "identity_hash": None,
            "claude_design_project": None,
            "variants": [],
            "last_verified_at": None,
        },
        "creator-registry.json": {
            "schema_version": "1.0",
            "campaign_id": args.campaign_id,
            "core": [],
            "rotating": [],
            "last_observed_at": None,
        },
        "gif-reference-index.json": {
            "schema_version": "1.0",
            "campaign_id": args.campaign_id,
            "references": [],
        },
        "creative-pattern-library.json": {
            "schema_version": "1.0",
            "campaign_id": args.campaign_id,
            "patterns": [],
        },
        "gif-creative-spec.json": {
            "schema_version": "1.0",
            "campaign_id": args.campaign_id,
            "selected_reference_id": None,
            "selected_pattern_id": None,
            "validation_status": "not-generated",
        },
        "premium-entitlements.json": {"schema_version": "1.0", "campaign_id": args.campaign_id, "products": []},
        "subscription-inventory.json": {
            "schema_version": "1.0",
            "campaign_id": args.campaign_id,
            "generated_at": None,
            "subscription": {},
            "features": [],
        },
        "subscription-utilization-plan.json": {
            "schema_version": "1.0",
            "campaign_id": args.campaign_id,
            "generated_at": None,
            "features": [],
            "summary": {},
        },
        "working-algorithm-model.json": {
            "schema_version": "1.0",
            "campaign_id": args.campaign_id,
            "version": "0.1",
            "strategy_weights": {"proven": 70, "promising": 20, "exploration": 10},
            "hypotheses": [],
        },
        "experiments.json": {"schema_version": "1.0", "campaign_id": args.campaign_id, "experiments": []},
    }.items():
        (state_dir / name).write_text(
            json.dumps(initial, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    for name in (
        "interaction-log.jsonl",
        "daily-analytics.jsonl",
        "learning-ledger.jsonl",
        "subscription-results.jsonl",
    ):
        (state_dir / name).touch()
    (state_dir / "logs").mkdir()
    (state_dir / "brand" / "watermarks").mkdir(parents=True)
    (state_dir / "gif-reference-captures").mkdir()

    print(json.dumps({"initialized": str(state_dir), "campaign_id": args.campaign_id}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
