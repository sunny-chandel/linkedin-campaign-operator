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
    "external-executor.template.json": "external-executor.json",
}

DEFAULT_CAMPAIGN_ID = "linkedin-growth"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state_dir", type=Path)
    parser.add_argument("--campaign-id", default=DEFAULT_CAMPAIGN_ID)
    parser.add_argument("--owner-name", required=True, help="LinkedIn profile display name")
    parser.add_argument("--profile-url", required=True, help="Full LinkedIn profile URL")
    parser.add_argument("--timezone", default="UTC", help="IANA timezone, for example Europe/London")
    parser.add_argument("--followers-baseline", type=int)
    parser.add_argument("--connections-baseline", type=int)
    parser.add_argument("--followers-goal", type=int, default=10000)
    parser.add_argument("--connections-goal", type=int, default=10000)
    parser.add_argument("--niche")
    args = parser.parse_args()

    if not args.profile_url.startswith("https://www.linkedin.com/in/"):
        parser.error("--profile-url must be a full https://www.linkedin.com/in/... URL")
    if args.followers_goal <= 0 or args.connections_goal <= 0:
        parser.error("growth goals must be positive")

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
            data["timezone"] = args.timezone
            data["target"]["metric_a"]["baseline"] = args.followers_baseline
            data["target"]["metric_b"]["baseline"] = args.connections_baseline
            data["target"]["metric_a"]["goal"] = args.followers_goal
            data["target"]["metric_b"]["goal"] = args.connections_goal
            data["target"]["name"] = f"{args.followers_goal}-followers-{args.connections_goal}-connections"
            data["target"]["completion_formula"] = (
                f"metric_a >= {args.followers_goal} and metric_b >= {args.connections_goal}"
            )
            data["publishing_optimization"]["production_priority_window"]["timezone"] = args.timezone
            if args.niche:
                data["audience"]["niche"] = args.niche
        if output_name == "consent-record.json":
            data["owner"] = {
                "display_name": args.owner_name,
                "expected_linkedin_identity": args.owner_name,
            }
            data["accounts"] = [
                {
                    "type": "linkedin-profile",
                    "owner": args.owner_name,
                    "url": args.profile_url,
                }
            ]
            data["data_directory"] = str(state_dir)
        if output_name == "campaign-state.json":
            data["updated_at"] = now
            data["dispatcher"]["browser_binding"]["expected_profile_url"] = args.profile_url
            data["dispatcher"]["browser_binding"]["expected_profile_name"] = args.owner_name
        if output_name == "external-executor.json":
            data["campaign_id"] = args.campaign_id
            accounts = data.get("credential_source", {}).get("keychain", {}).get("accounts", {})
            if isinstance(accounts, dict):
                for key in list(accounts):
                    accounts[key] = f"{args.campaign_id}:{key.replace('_', '-')}"
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
            "schema_version": "2.0",
            "campaign_id": args.campaign_id,
            "version": "6.0.0-rc.8",
            "strategy_weights": {"proven": 70, "promising": 20, "exploration": 10},
            "scheduling_models": {
                "publication_timing": {"mode": "evidence-adaptive", "observations": []},
                "response_latency": {"mode": "evidence-adaptive", "observations": []},
                "regional_opportunity": {"mode": "evidence-adaptive", "observations": []},
                "concentration": {"mode": "evidence-adaptive", "observations": []},
                "candidate_staleness": {"mode": "evidence-adaptive", "observations": []},
                "source_yield": {"mode": "evidence-adaptive", "observations": []},
                "gate_tier": {"mode": "evidence-adaptive", "observations": []},
                "action_type": {"mode": "evidence-adaptive", "observations": []},
                "recovery_post": {"mode": "evidence-adaptive", "observations": []},
                "action_to_profile_view": {"mode": "evidence-adaptive", "observations": []},
                "follower_conversion": {"mode": "evidence-adaptive", "observations": []},
                "format_performance": {"mode": "evidence-adaptive", "observations": []},
                "topic_performance": {"mode": "evidence-adaptive", "observations": []},
                "regional_spillover": {"mode": "evidence-adaptive", "observations": []},
            },
            "hypotheses": [],
        },
        "experiments.json": {"schema_version": "1.0", "campaign_id": args.campaign_id, "experiments": []},
        "work-queue.json": {
            "schema_version": "2.0",
            "campaign_id": args.campaign_id,
            "updated_at": now,
            "items": [],
        },
        "stage-ledger.json": {
            "schema_version": "2.0",
            "campaign_id": args.campaign_id,
            "updated_at": now,
            "stages": [],
        },
        "engagement-opportunities.json": {
            "schema_version": "2.0",
            "campaign_id": args.campaign_id,
            "updated_at": now,
            "opportunities": [],
        },
        "operational-output.json": {
            "schema_version": "2.0",
            "campaign_id": args.campaign_id,
            "calculated_at": now,
            "window": {"hours": 24, "start_at": None, "end_at": now},
            "actions": {
                "rolling_24h_actions": 0,
                "target": 160,
                "hard_cap": 200,
                "debt": 160,
                "remaining_capacity": 200,
                "target_met": False,
                "cap_reached": False,
                "checkpoints": [40, 80, 120, 160],
                "checkpoints_reached": [],
                "direct_inbound_replies": 0,
                "direct_inbound_outside_cap": True,
                "evidence_file": "interaction-log.jsonl",
            },
            "publishing": {
                "rolling_24h_posts": 0,
                "target": 6,
                "hard_cap": 8,
                "debt": 6,
                "remaining_capacity": 8,
                "target_met": False,
                "cap_reached": False,
                "verified_post_ids": [],
                "evidence_file": "publication-evidence.jsonl",
            },
        },
        "content-pipeline.json": {
            "schema_version": "2.0",
            "campaign_id": args.campaign_id,
            "topic_candidates": [],
            "briefs": [],
            "packages": [],
            "inventory": {"target": 6, "validated_unpublished": 0, "debt": 6},
            "analytics_schedule": [],
            "replacement_requirements": [],
        },
        "regional-performance.json": {
            "schema_version": "2.0",
            "campaign_id": args.campaign_id,
            "observations": [],
            "current_allocation": {
                "mode": "bootstrap",
                "six_post_allocation": ["india", "india", "us", "us", "uk-eu", "apac"],
                "observation_count": 0,
            },
            "exploration_state": {"proven": 70, "promising": 20, "exploration": 10},
        },
        "repair-state.json": {
            "schema_version": "2.0",
            "campaign_id": args.campaign_id,
            "status": "healthy",
            "active_repair": None,
            "history": [],
        },
    }.items():
        (state_dir / name).write_text(
            json.dumps(initial, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    for name in (
        "interaction-log.jsonl",
        "daily-analytics.jsonl",
        "learning-ledger.jsonl",
        "subscription-results.jsonl",
        "signal-events.jsonl",
        "schedule-decisions.jsonl",
        "publication-evidence.jsonl",
        "task-events.jsonl",
        "recovery-events.jsonl",
        "opportunity-health.jsonl",
        "repair-events.jsonl",
        "external-executor-events.jsonl",
    ):
        (state_dir / name).touch()
    (state_dir / "logs").mkdir()
    (state_dir / "brand" / "watermarks").mkdir(parents=True)
    for status in ("pending", "running", "verified", "deferred", "ambiguous", "failed"):
        (state_dir / "external-action-outbox" / status).mkdir(parents=True, exist_ok=True)
    (state_dir / "gif-reference-captures").mkdir()

    print(json.dumps({"initialized": str(state_dir), "campaign_id": args.campaign_id}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
