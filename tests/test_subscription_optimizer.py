#!/usr/bin/env python3
"""Regression tests for subscription scoring and campaign migration."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "linkedin-campaign-operator-v3"
SCORER = PLUGIN / "skills" / "linkedin-premium-router" / "scripts" / "score_subscription_features.py"
ORCHESTRATOR_SCRIPTS = PLUGIN / "skills" / "linkedin-campaign-orchestrator" / "scripts"


class SubscriptionOptimizerTests(unittest.TestCase):
    def test_scoring_uses_verified_capacity_and_marks_unavailable(self) -> None:
        inventory = {
            "schema_version": "1.0",
            "campaign_id": "test",
            "features": [
                {
                    "feature_id": "high",
                    "entitled": True,
                    "quota_total": 100,
                    "quota_used": 20,
                    "campaign_relevance": 1,
                    "evidence_strength": 1,
                    "expiry_urgency": 0.5,
                    "implementation_readiness": 1,
                },
                {
                    "feature_id": "unknown-capacity",
                    "entitled": True,
                    "campaign_relevance": 0.4,
                    "evidence_strength": 0.4,
                    "expiry_urgency": 0,
                    "implementation_readiness": 0.5,
                },
                {
                    "feature_id": "unavailable",
                    "entitled": False,
                    "unused_capacity": 1,
                    "campaign_relevance": 1,
                    "evidence_strength": 1,
                    "expiry_urgency": 1,
                    "implementation_readiness": 1,
                },
            ],
        }
        with tempfile.TemporaryDirectory() as temporary:
            inventory_path = Path(temporary) / "inventory.json"
            inventory_path.write_text(json.dumps(inventory), encoding="utf-8")
            completed = subprocess.run(
                ["python3", str(SCORER), str(inventory_path)],
                check=True,
                capture_output=True,
                text=True,
            )
        plan = json.loads(completed.stdout)
        features = {item["feature_id"]: item for item in plan["features"]}
        self.assertEqual(plan["features"][0]["feature_id"], "high")
        self.assertEqual(features["high"]["score_components"]["unused_capacity"], 0.8)
        self.assertEqual(features["unknown-capacity"]["score_components"]["unused_capacity"], 0)
        self.assertEqual(features["unknown-capacity"]["unused_capacity_source"], "unknown")
        self.assertEqual(features["unavailable"]["score"], 0)
        self.assertEqual(features["unavailable"]["status"], "unavailable")

    def test_existing_campaign_migrates_without_overwriting_values(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state_dir = Path(temporary) / "campaign"
            subprocess.run(
                [
                    "python3",
                    str(ORCHESTRATOR_SCRIPTS / "init_campaign.py"),
                    str(state_dir),
                    "--owner-name",
                    "Test Operator",
                    "--profile-url",
                    "https://www.linkedin.com/in/test-operator/",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                [
                    "python3",
                    str(ORCHESTRATOR_SCRIPTS / "runtime_control.py"),
                    str(state_dir),
                    "--now",
                    "2026-08-25T12:00:00+05:30",
                    "consent-grant",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            config_path = state_dir / "campaign-config.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["audience"]["niche"] = "preserve-me"
            config.pop("subscription_optimization")
            config_path.write_text(json.dumps(config), encoding="utf-8")
            state_path = state_dir / "campaign-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state.pop("subscription_optimization")
            state_path.write_text(json.dumps(state), encoding="utf-8")
            for name in (
                "subscription-inventory.json",
                "subscription-utilization-plan.json",
                "subscription-results.jsonl",
            ):
                (state_dir / name).unlink()
            subprocess.run(
                [
                    "python3",
                    str(ORCHESTRATOR_SCRIPTS / "migrate_campaign.py"),
                    str(state_dir),
                    "--now",
                    "2026-08-25T12:00:00+05:30",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            migrated = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(migrated["audience"]["niche"], "preserve-me")
            self.assertTrue(migrated["subscription_optimization"]["enabled"])
            consent = json.loads((state_dir / "consent-record.json").read_text(encoding="utf-8"))
            self.assertEqual(consent["consent_version"], "2.0")
            self.assertEqual(consent["scope"], "campaign-lifetime")
            self.assertFalse(consent["reconfirmation_policy"]["routine_reconfirmation_required"])
            self.assertIn("adaptive-100-base-action-ceiling", consent["persistent_settings"])
            self.assertNotIn("adaptive-80-action-ceiling", consent["persistent_settings"])
            migrated_state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(migrated_state["subscription_optimization"]["active_features"], [])
            self.assertEqual(migrated_state["engagement_scaling"]["base_daily_ceiling"], 100)
            self.assertTrue((state_dir / "subscription-inventory.json").is_file())
            self.assertTrue((state_dir / "subscription-utilization-plan.json").is_file())
            self.assertTrue((state_dir / "subscription-results.jsonl").is_file())
            self.assertTrue((state_dir / "watermark-manifest.json").is_file())
            self.assertTrue((state_dir / "creator-registry.json").is_file())
            self.assertTrue((state_dir / "creative-pattern-library.json").is_file())
            self.assertTrue((state_dir / "gif-reference-captures").is_dir())
            validated = subprocess.run(
                ["python3", str(ORCHESTRATOR_SCRIPTS / "validate_campaign.py"), str(state_dir)],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertTrue(json.loads(validated.stdout)["valid"])


if __name__ == "__main__":
    unittest.main()
