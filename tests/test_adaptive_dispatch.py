#!/usr/bin/env python3
"""Acceptance tests for the public v1.1 reliable adaptive dispatcher and state model."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "linkedin-campaign-operator-v3"
ORCHESTRATOR = PLUGIN / "skills" / "linkedin-campaign-orchestrator" / "scripts"
ENGAGEMENT = PLUGIN / "skills" / "linkedin-engagement-planning" / "scripts"
TEST_NOW = "2026-08-25T12:00:00+05:30"


def run_json(arguments: list[str]) -> dict:
    script_name = Path(arguments[1]).name if len(arguments) > 1 else ""
    if script_name in {"dispatch_next_work.py", "migrate_campaign.py", "audit_pipeline.py"} and "--now" not in arguments:
        arguments = [*arguments, "--now", TEST_NOW]
    completed = subprocess.run(arguments, check=True, capture_output=True, text=True)
    return json.loads(completed.stdout)


def run_failure(arguments: list[str]) -> dict:
    completed = subprocess.run(arguments, check=False, capture_output=True, text=True)
    if completed.returncode == 0:
        raise AssertionError(f"command unexpectedly succeeded: {arguments}")
    return json.loads(completed.stderr)


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


class AdaptiveDispatchTests(unittest.TestCase):
    def init_campaign(self, root: Path) -> Path:
        state_dir = root / "campaign"
        run_json(
            [
                "python3",
                str(ORCHESTRATOR / "init_campaign.py"),
                str(state_dir),
                "--owner-name",
                "Test Operator",
                "--profile-url",
                "https://www.linkedin.com/in/test-operator/",
                "--timezone",
                "Asia/Kolkata",
            ]
        )
        logs = state_dir / "logs"
        for region in ("india", "us-central"):
            write_json(
                logs / f"publication-package-{region}-2026-08-25.json",
                {
                    "content_day_ist": "2026-08-25",
                    "target_region": region,
                    "final_validation_status": "ready-to-publish",
                },
            )
        run_json(
            [
                "python3",
                str(ORCHESTRATOR / "runtime_control.py"),
                str(state_dir),
                "--now",
                TEST_NOW,
                "consent-grant",
            ]
        )
        run_json(
            [
                "python3",
                str(ORCHESTRATOR / "resume_campaign.py"),
                str(state_dir),
                "--now",
                TEST_NOW,
                "--session-id",
                "test-session",
            ]
        )
        ledger_path = state_dir / "stage-ledger.json"
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        for stage in ledger["stages"]:
            stage["status"] = "completed" if stage.get("stage_type") == "preflight" else "cancelled"
        write_json(ledger_path, ledger)
        queue_path = state_dir / "work-queue.json"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        for item in queue["items"]:
            item["status"] = "completed"
        write_json(queue_path, queue)
        state_path = state_dir / "campaign-state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["publishing"]["posts_published"] = 2
        state["publishing"]["published_post_ids"] = ["test-india", "test-us"]
        write_json(state_path, state)
        return state_dir

    def test_prepared_post_without_queue_builds_queue_instead_of_waiting(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state_dir = self.init_campaign(Path(temporary))
            state = json.loads((state_dir / "campaign-state.json").read_text(encoding="utf-8"))
            state["publishing"]["packages_ready"] = 2
            state["publishing"]["posts_published"] = 0
            state["publishing"]["published_post_ids"] = []
            write_json(state_dir / "campaign-state.json", state)
            queue = {
                "schema_version": "1.0",
                "campaign_id": "linkedin-growth",
                "items": [
                    {
                        "task_id": "publish-india",
                        "task_type": "publication-opportunity",
                        "lane": "linkedin",
                        "priority": 3,
                        "status": "pending",
                        "ready": True,
                        "requires_linkedin": True,
                        "engagement_queue_ready": False,
                    }
                ],
            }
            write_json(state_dir / "work-queue.json", queue)
            result = run_json(["python3", str(ORCHESTRATOR / "dispatch_next_work.py"), str(state_dir)])
            self.assertEqual(result["decision"], "execute")
            self.assertEqual(result["task"]["task_type"], "publication-queue-building")

    def test_missing_analytics_cannot_be_completed_and_recovers_offline(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state_dir = self.init_campaign(Path(temporary))
            (state_dir / "daily-analytics.jsonl").write_text('{"impressions": 10}\n', encoding="utf-8")
            ledger = json.loads((state_dir / "stage-ledger.json").read_text(encoding="utf-8"))
            ledger["stages"].append(
                {
                    "stage_id": "analytics-today",
                    "stage_type": "analytics",
                    "status": "completed",
                    "required_artifacts": ["daily-analytics.jsonl", "learning-ledger.jsonl"],
                    "learning_recorded": False,
                    "experiment_outcome": None,
                    "next_measurement_trigger": None,
                }
            )
            write_json(state_dir / "stage-ledger.json", ledger)
            audit = run_json(
                ["python3", str(ORCHESTRATOR / "audit_pipeline.py"), str(state_dir), "--write"]
            )
            self.assertFalse(audit["valid"])
            self.assertEqual(audit["invalid_completion_claims"], 1)
            self.assertEqual(audit["recovery_tasks"][0]["lane"], "offline")
            decision = run_json(
                ["python3", str(ORCHESTRATOR / "dispatch_next_work.py"), str(state_dir)]
            )
            self.assertEqual(decision["task"]["task_type"], "mandatory-stage-recovery")

    def test_soft_reciprocity_selects_one_qualified_post_and_rejects_cooldown(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            candidates = Path(temporary) / "candidates.json"
            high = {
                "lane": "soft-reciprocity",
                "target_status": "new",
                "follower_count": 4000,
                "action_available": True,
                "cooldown_passed": True,
                "triggering_signal": "like",
                "qualified_growth": 0.9,
                "audience_spillover": 0.9,
                "conversation_probability": 0.8,
                "target_relevance": 0.9,
                "freshness_timing": 0.9,
                "historical_performance": 0.8,
            }
            write_json(
                candidates,
                {
                    "budget": {"base_daily_ceiling": 100, "base_actions_used": 0},
                    "candidates": [
                        {**high, "candidate_id": "post-a", "target_id": "liker-1"},
                        {**high, "candidate_id": "post-b", "target_id": "liker-1", "qualified_growth": 0.8},
                        {**high, "candidate_id": "cooling", "target_id": "liker-2", "cooldown_passed": False},
                        {**high, "candidate_id": "low", "target_id": "liker-3", "qualified_growth": 0.1, "audience_spillover": 0.1, "conversation_probability": 0.1, "target_relevance": 0.1, "freshness_timing": 0.1, "historical_performance": 0.1},
                    ],
                },
            )
            ranked = run_json(["python3", str(ENGAGEMENT / "rank_actions.py"), str(candidates)])
            self.assertEqual([item["candidate_id"] for item in ranked["selected"]], ["post-a"])
            rejected = {item["candidate_id"]: item for item in ranked["rejected"]}
            self.assertEqual(rejected["post-b"]["reason"], "soft-reciprocity-one-opportunity")
            self.assertIn("cooldown_passed", rejected["cooling"]["failed_gates"])
            self.assertEqual(rejected["low"]["reason"], "below-threshold")

    def test_direct_reply_after_100_uses_overage_while_other_lanes_stop(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidates = root / "candidates.json"
            common = {
                "action_available": True,
                "qualified": True,
                "cooldown_passed": True,
                "qualified_growth": 1,
                "audience_spillover": 1,
                "conversation_probability": 1,
                "target_relevance": 1,
                "freshness_timing": 1,
                "historical_performance": 1,
            }
            write_json(
                candidates,
                {
                    "budget": {"base_daily_ceiling": 100, "base_actions_used": 100, "direct_reply_overage": 4},
                    "candidates": [
                        {**common, "candidate_id": "reply", "lane": "direct-inbound"},
                        {**common, "candidate_id": "proactive", "lane": "proactive"},
                        {**common, "candidate_id": "soft", "lane": "soft-reciprocity", "triggering_signal": "follow"},
                    ],
                },
            )
            ranked = run_json(["python3", str(ENGAGEMENT / "rank_actions.py"), str(candidates)])
            self.assertEqual([item["candidate_id"] for item in ranked["selected"]], ["reply"])
            self.assertEqual(ranked["selected"][0]["budget_class"], "direct-reply-overage")
            self.assertEqual(ranked["projected_budget"]["direct_reply_overage"], 5)
            rejected = {item["candidate_id"]: item for item in ranked["rejected"]}
            self.assertIn("base_daily_ceiling", rejected["proactive"]["failed_gates"])
            self.assertIn("base_daily_ceiling", rejected["soft"]["failed_gates"])

            state_dir = self.init_campaign(root)
            state = json.loads((state_dir / "campaign-state.json").read_text(encoding="utf-8"))
            state["engagement_scaling"]["budget_day_local"] = "2026-08-25"
            state["engagement_scaling"]["base_actions_used"] = 100
            write_json(state_dir / "campaign-state.json", state)
            action = root / "action.json"
            write_json(
                action,
                {
                    "action_id": "reply-101",
                    "lane": "direct-inbound",
                    "triggering_signal": "comment:123",
                    "relationship_strength": 0.4,
                    "scheduling_rationale": "fresh genuine inbound comment",
                },
            )
            recorded = run_json(
                ["python3", str(ENGAGEMENT / "record_action.py"), str(state_dir), str(action), "--now", "2026-08-25T12:00:00+05:30"]
            )
            self.assertEqual(recorded["base_actions_used"], 100)
            self.assertEqual(recorded["direct_reply_overage"], 1)

    def test_dynamic_publishing_requires_exact_pair_and_rejects_third(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            opportunity = root / "opportunity.json"
            posts = [
                {"post_id": "india", "region": "india", "ready": True, "published": False},
                {"post_id": "us", "region": "us-central", "ready": True, "published": False},
            ]
            write_json(
                opportunity,
                {
                    "posts": posts,
                    "opportunities": [
                        {
                            "post_id": "india",
                            "observed_at": "2026-08-25T04:00:00Z",
                            "regional_activity": 0.9,
                            "qualified_target_activity": 0.9,
                            "topic_freshness": 0.8,
                            "network_velocity": 0.8,
                            "historical_equal_age": 0.9,
                            "format_pillar_fit": 0.9,
                            "remaining_day_opportunity": 0.7,
                            "cannibalization_risk": 0.1,
                        }
                    ],
                },
            )
            selected = run_json(
                ["python3", str(ORCHESTRATOR / "select_publish_time.py"), str(opportunity)]
            )
            self.assertEqual(selected["decision"], "publish-now")
            self.assertFalse(selected["fixed_publish_time_used"])
            self.assertFalse(selected["fixed_spacing_used"])
            invalid = json.loads(opportunity.read_text(encoding="utf-8"))
            invalid["posts"].append({"post_id": "third", "region": "uk-eu", "ready": True})
            write_json(opportunity, invalid)
            error = run_failure(
                ["python3", str(ORCHESTRATOR / "select_publish_time.py"), str(opportunity)]
            )
            self.assertIn("exactly two", error["error"])

    def test_bursts_cap_at_ten_and_weak_queue_does_not_force_actions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidates = root / "candidates.json"
            write_json(
                candidates,
                {
                    "candidates": [
                        {
                            "candidate_id": "weak",
                            "lane": "proactive",
                            "qualified": True,
                            "cooldown_passed": True,
                            "action_available": True,
                            "qualified_growth": 0.1,
                            "audience_spillover": 0.1,
                            "conversation_probability": 0.1,
                            "target_relevance": 0.1,
                            "freshness_timing": 0.1,
                            "historical_performance": 0.1,
                        }
                    ]
                },
            )
            ranked = run_json(["python3", str(ENGAGEMENT / "rank_actions.py"), str(candidates)])
            self.assertEqual(ranked["selected"], [])
            failed = subprocess.run(
                ["python3", str(ENGAGEMENT / "rank_actions.py"), str(candidates), "--limit", "11"],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(failed.returncode, 0)
            self.assertIn("limit", failed.stderr)
            state_dir = self.init_campaign(root)
            state = json.loads((state_dir / "campaign-state.json").read_text(encoding="utf-8"))
            state["engagement_scaling"]["base_actions_used"] = 100
            write_json(state_dir / "campaign-state.json", state)
            decision = run_json(
                ["python3", str(ORCHESTRATOR / "dispatch_next_work.py"), str(state_dir)]
            )
            self.assertEqual(decision["decision"], "execute")
            self.assertEqual(decision["task"]["task_type"], "analytics-and-investigation")

    def test_chrome_blocker_keeps_offline_lane_running_and_status_is_separated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state_dir = self.init_campaign(Path(temporary))
            state = json.loads((state_dir / "campaign-state.json").read_text(encoding="utf-8"))
            state["dispatcher"]["linkedin_lane"] = "blocked"
            state["engagement_scaling"]["base_actions_used"] = 37
            state["engagement_scaling"]["direct_reply_overage"] = 2
            state["publishing"]["packages_ready"] = 1
            state["publishing"]["posts_published"] = 1
            write_json(state_dir / "campaign-state.json", state)
            write_json(
                state_dir / "work-queue.json",
                {
                    "schema_version": "1.0",
                    "campaign_id": "linkedin-growth",
                    "items": [
                        {"task_id": "linkedin", "task_type": "soft-reciprocity", "action_lane": "soft-reciprocity", "lane": "linkedin", "priority": 2, "status": "pending", "ready": True, "requires_linkedin": True},
                        {"task_id": "offline", "task_type": "analytics-and-investigation", "lane": "offline", "priority": 8, "status": "pending", "ready": True, "requires_linkedin": False},
                    ],
                },
            )
            decision = run_json(
                ["python3", str(ORCHESTRATOR / "dispatch_next_work.py"), str(state_dir)]
            )
            self.assertEqual(decision["task"]["task_id"], "offline")
            status = run_json(["python3", str(ORCHESTRATOR / "campaign_status.py"), str(state_dir)])
            self.assertEqual(status["posting"]["posts_published"], 1)
            self.assertEqual(status["engagement"]["base_actions_used"], 37)
            self.assertEqual(status["engagement"]["direct_reply_overage"], 2)
            self.assertEqual(status["blockers"]["linkedin_lane"], "blocked")
            self.assertFalse(status["true_idle"])

    def test_wait_requires_empty_queue_and_evidence_backed_trigger(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state_dir = self.init_campaign(Path(temporary))
            state = json.loads((state_dir / "campaign-state.json").read_text(encoding="utf-8"))
            state["engagement_scaling"]["base_actions_used"] = 100
            write_json(state_dir / "campaign-state.json", state)
            first = run_json(["python3", str(ORCHESTRATOR / "dispatch_next_work.py"), str(state_dir)])
            self.assertEqual(first["decision"], "execute")
            state = json.loads((state_dir / "campaign-state.json").read_text(encoding="utf-8"))
            state["dispatcher"]["next_wake_at"] = "2026-08-25T12:00:00+05:30"
            state["dispatcher"]["next_wake_reason"] = "predicted qualified inbound check"
            write_json(state_dir / "campaign-state.json", state)
            waited = run_json(
                [
                    "python3",
                    str(ORCHESTRATOR / "dispatch_next_work.py"),
                    str(state_dir),
                    "--record",
                    "--now",
                    "2026-08-25T11:00:00+05:30",
                ]
            )
            self.assertEqual(waited["decision"], "wait")
            self.assertEqual(waited["unfinished_work_count"], 0)
            self.assertIn("validated work queue", waited["evidence"])
            persisted = json.loads((state_dir / "campaign-state.json").read_text(encoding="utf-8"))
            self.assertEqual(persisted["dispatcher"]["last_decision_at"], waited["decided_at"])
            self.assertEqual(persisted["dispatcher"]["unfinished_work_count"], 0)
            self.assertEqual(persisted["engagement_scaling"]["budget_day_local"], "2026-08-25")

    def test_public_initializer_accepts_custom_identity_timezone_and_goals(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state_dir = Path(temporary) / "public-campaign"
            run_json(
                [
                    "python3",
                    str(ORCHESTRATOR / "init_campaign.py"),
                    str(state_dir),
                    "--owner-name",
                    "Ada Example",
                    "--profile-url",
                    "https://www.linkedin.com/in/ada-example/",
                    "--timezone",
                    "America/New_York",
                    "--followers-goal",
                    "25000",
                    "--connections-goal",
                    "7500",
                    "--niche",
                    "developer tools",
                ]
            )
            validated = run_json(
                [
                    "python3",
                    str(ORCHESTRATOR / "validate_campaign.py"),
                    str(state_dir),
                    "--allow-draft",
                ]
            )
            self.assertTrue(validated["valid"])
            config = json.loads((state_dir / "campaign-config.json").read_text(encoding="utf-8"))
            consent = json.loads((state_dir / "consent-record.json").read_text(encoding="utf-8"))
            self.assertEqual(config["timezone"], "America/New_York")
            self.assertEqual(config["target"]["metric_a"]["goal"], 25000)
            self.assertEqual(config["target"]["metric_b"]["goal"], 7500)
            self.assertEqual(config["audience"]["niche"], "developer tools")
            self.assertEqual(consent["owner"]["display_name"], "Ada Example")
            self.assertEqual(consent["accounts"][0]["url"], "https://www.linkedin.com/in/ada-example/")

    def test_migration_preserves_history_and_converts_80_to_100(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state_dir = self.init_campaign(root)
            config_path = state_dir / "campaign-config.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["schema_version"] = "1.0"
            config["fixed_rules"].update({"max_actions_per_day": 80, "max_actions_per_cluster": 10})
            config.pop("adaptive_dispatch")
            config.pop("publishing_optimization")
            config["engagement_optimization"]["clusters"] = [{"cluster_id": 1}]
            write_json(config_path, config)
            state_path = state_dir / "campaign-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["schema_version"] = "1.0"
            state["engagement_scaling"] = {
                "daily_ceiling": 80,
                "actions_executed_today": 69,
                "completed_clusters": [1, 2],
            }
            state["scheduled_work"] = [{"id": "legacy-scheduled"}]
            state["today"] = {"date_ist": "2026-08-25", "window_2_india_published": True}
            write_json(state_path, state)
            (state_dir / "interaction-log.jsonl").write_text('{"action_id":"historic"}\n', encoding="utf-8")
            write_json(state_dir / "experiments.json", {"experiments": [{"id": "preserve"}]})
            write_json(state_dir / "publication-evidence.json", {"post_id": "historic-post"})
            for name in ("work-queue.json", "stage-ledger.json", "signal-events.jsonl", "schedule-decisions.jsonl"):
                (state_dir / name).unlink()
            run_json(["python3", str(ORCHESTRATOR / "migrate_campaign.py"), str(state_dir)])
            migrated_config = json.loads(config_path.read_text(encoding="utf-8"))
            migrated_state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(migrated_config["fixed_rules"]["base_actions_per_day"], 100)
            self.assertEqual(
                migrated_config["adaptive_dispatch"]["priority_order"][0],
                "technical-session-or-identity-recovery",
            )
            self.assertNotIn("max_actions_per_day", migrated_config["fixed_rules"])
            self.assertNotIn("clusters", migrated_config["engagement_optimization"])
            self.assertEqual(migrated_state["engagement_scaling"]["base_actions_used"], 69)
            self.assertEqual(migrated_state["engagement_scaling"]["base_daily_ceiling"], 100)
            self.assertEqual(len(migrated_state["engagement_scaling"]["burst_history"]), 2)
            self.assertEqual(migrated_state["scheduled_work"], [{"id": "legacy-scheduled"}])
            self.assertIn("historic", (state_dir / "interaction-log.jsonl").read_text(encoding="utf-8"))
            self.assertEqual(json.loads((state_dir / "experiments.json").read_text(encoding="utf-8"))["experiments"][0]["id"], "preserve")
            self.assertTrue((state_dir / "publication-evidence.json").is_file())
            production_task = next(
                item
                for item in json.loads((state_dir / "work-queue.json").read_text(encoding="utf-8"))["items"]
                if item["task_type"] == "two-package-production"
            )
            self.assertEqual(production_task["required_regions"], ["india", "us-central"])
            self.assertEqual(production_task["required_package_count"], 2)
            validated = run_json(["python3", str(ORCHESTRATOR / "validate_campaign.py"), str(state_dir)])
            self.assertTrue(validated["valid"])

    def test_migration_normalizes_first_priority_to_technical_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state_dir = self.init_campaign(Path(temporary))
            config_path = state_dir / "campaign-config.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["adaptive_dispatch"]["priority_order"][0] = "legacy-first-priority"
            write_json(config_path, config)
            run_json(["python3", str(ORCHESTRATOR / "migrate_campaign.py"), str(state_dir)])
            migrated = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(
                migrated["adaptive_dispatch"]["priority_order"][0],
                "technical-session-or-identity-recovery",
            )

    def test_one_time_consent_persists_across_session_restart(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state_dir = Path(temporary) / "campaign"
            run_json(
                [
                    "python3",
                    str(ORCHESTRATOR / "init_campaign.py"),
                    str(state_dir),
                    "--owner-name",
                    "Test Operator",
                    "--profile-url",
                    "https://www.linkedin.com/in/test-operator/",
                    "--timezone",
                    "Asia/Kolkata",
                ]
            )
            before = run_json(
                ["python3", str(ORCHESTRATOR / "dispatch_next_work.py"), str(state_dir)]
            )
            self.assertEqual(before["decision"], "consent-required")
            granted = run_json(
                [
                    "python3",
                    str(ORCHESTRATOR / "runtime_control.py"),
                    str(state_dir),
                    "--now",
                    TEST_NOW,
                    "consent-grant",
                ]
            )
            restarted = run_json(
                [
                    "python3",
                    str(ORCHESTRATOR / "resume_campaign.py"),
                    str(state_dir),
                    "--now",
                    "2026-08-25T13:00:00+05:30",
                    "--session-id",
                    "replacement-model-session",
                ]
            )
            granted_again = run_json(
                [
                    "python3",
                    str(ORCHESTRATOR / "runtime_control.py"),
                    str(state_dir),
                    "--now",
                    "2026-08-25T13:01:00+05:30",
                    "consent-grant",
                ]
            )
            self.assertTrue(restarted["self_revived"])
            self.assertTrue(granted_again["already_active"])
            self.assertEqual(granted["receipt_id"], granted_again["receipt_id"])

    def test_browser_binding_is_reused_and_preflight_evidence_is_cached(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state_dir = self.init_campaign(Path(temporary))
            first = run_json(
                [
                    "python3",
                    str(ORCHESTRATOR / "runtime_control.py"),
                    str(state_dir),
                    "--now",
                    TEST_NOW,
                    "browser-bind",
                    "--device-id",
                    "local-mac",
                    "--device-label",
                    "Sunny Mac",
                    "--platform",
                    "macOS",
                    "--identity-verified",
                ]
            )
            failed = run_failure(
                [
                    "python3",
                    str(ORCHESTRATOR / "runtime_control.py"),
                    str(state_dir),
                    "--now",
                    TEST_NOW,
                    "browser-bind",
                    "--device-id",
                    "remote-windows",
                ]
            )
            run_json(
                [
                    "python3",
                    str(ORCHESTRATOR / "runtime_control.py"),
                    str(state_dir),
                    "--now",
                    TEST_NOW,
                    "preflight-record",
                    "--component",
                    "browser",
                    "--status",
                    "passed",
                    "--evidence",
                    "connected local macOS",
                ]
            )
            cached = run_json(
                [
                    "python3",
                    str(ORCHESTRATOR / "runtime_control.py"),
                    str(state_dir),
                    "--now",
                    "2026-08-25T12:15:00+05:30",
                    "preflight-status",
                ]
            )
            self.assertEqual(first["browser_binding"]["device_id"], "local-mac")
            self.assertIn("already pinned", failed["error"])
            self.assertIn("browser", cached["reusable_components"])

    def test_restart_expires_lease_and_rolls_to_current_content_day(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state_dir = self.init_campaign(Path(temporary))
            logs = state_dir / "logs"
            for region in ("india", "us-central"):
                write_json(
                    logs / f"publication-package-{region}-2026-08-26.json",
                    {
                        "content_day_ist": "2026-08-26",
                        "target_region": region,
                        "final_validation_status": "ready-to-publish",
                    },
                )
            queue = {
                "schema_version": "1.1",
                "campaign_id": "sunny-linkedin-10k-10k",
                "items": [
                    {
                        "task_id": "offline-checkpointed",
                        "task_type": "analytics-and-investigation",
                        "lane": "offline",
                        "priority": 8,
                        "status": "running",
                        "ready": True,
                        "requires_linkedin": False,
                        "lease_id": "old-lease",
                        "lease_expires_at": "2026-08-26T00:10:00+05:30",
                        "checkpoint": {"sources_saved": 3},
                    }
                ],
            }
            write_json(state_dir / "work-queue.json", queue)
            revived = run_json(
                [
                    "python3",
                    str(ORCHESTRATOR / "resume_campaign.py"),
                    str(state_dir),
                    "--now",
                    "2026-08-26T01:00:00+05:30",
                    "--session-id",
                    "after-machine-restart",
                ]
            )
            state = json.loads((state_dir / "campaign-state.json").read_text(encoding="utf-8"))
            tasks = json.loads((state_dir / "work-queue.json").read_text(encoding="utf-8"))["items"]
            recovered = next(item for item in tasks if item["task_id"] == "offline-checkpointed")
            publication_ids = {item["task_id"] for item in tasks if item["task_type"] == "publication-opportunity"}
            self.assertTrue(revived["content_day"]["rollover_performed"])
            self.assertEqual(state["publishing"]["content_day_ist"], "2026-08-26")
            self.assertEqual(state["publishing"]["posts_published"], 0)
            self.assertEqual(recovered["status"], "recovering")
            self.assertEqual(recovered["checkpoint"]["sources_saved"], 3)
            self.assertIn("publish-india-2026-08-26", publication_ids)
            self.assertIn("publish-us-central-2026-08-26", publication_ids)

    def test_lane_circuit_breaker_routes_to_offline_work_and_auto_probe(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state_dir = self.init_campaign(Path(temporary))
            for minute in (0, 1):
                run_json(
                    [
                        "python3",
                        str(ORCHESTRATOR / "runtime_control.py"),
                        str(state_dir),
                        "--now",
                        f"2026-08-25T12:0{minute}:00+05:30",
                        "lane-event",
                        "--lane",
                        "linkedin",
                        "--event",
                        "transient-failure",
                        "--reason",
                        "page loading stalled",
                    ]
                )
            queue = json.loads((state_dir / "work-queue.json").read_text(encoding="utf-8"))
            queue["items"].append(
                {
                    "task_id": "offline-during-circuit",
                    "task_type": "analytics-and-investigation",
                    "lane": "offline",
                    "priority": 8,
                    "status": "pending",
                    "ready": True,
                    "requires_linkedin": False,
                }
            )
            write_json(state_dir / "work-queue.json", queue)
            during = run_json(
                [
                    "python3",
                    str(ORCHESTRATOR / "dispatch_next_work.py"),
                    str(state_dir),
                    "--now",
                    "2026-08-25T12:02:00+05:30",
                ]
            )
            probe = run_json(
                [
                    "python3",
                    str(ORCHESTRATOR / "dispatch_next_work.py"),
                    str(state_dir),
                    "--now",
                    "2026-08-25T12:17:00+05:30",
                ]
            )
            self.assertEqual(during["task"]["task_id"], "offline-during-circuit")
            self.assertEqual(probe["task"]["task_type"], "lane-recovery-probe")

    def test_reserve_target_is_adaptive_and_low_yield_pass_backs_off(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state_dir = self.init_campaign(Path(temporary))
            queue = json.loads((state_dir / "work-queue.json").read_text(encoding="utf-8"))
            queue["items"].append(
                {
                    "task_id": "reserve-pass-test",
                    "task_type": "adaptive-reserve",
                    "lane": "linkedin",
                    "priority": 6,
                    "status": "running",
                    "ready": True,
                    "requires_linkedin": True,
                }
            )
            write_json(state_dir / "work-queue.json", queue)
            result = run_json(
                [
                    "python3",
                    str(ORCHESTRATOR / "runtime_control.py"),
                    str(state_dir),
                    "--now",
                    TEST_NOW,
                    "reserve-pass",
                    "--task-id",
                    "reserve-pass-test",
                    "--pages",
                    "5",
                    "--elapsed-minutes",
                    "8",
                    "--inspected",
                    "12",
                    "--qualified-found",
                    "1",
                    "--qualified-total",
                    "1",
                    "--rejected",
                    "0",
                ]
            )
            self.assertNotEqual(result["reserve"]["target_count"], 20)
            self.assertTrue(result["stopping_condition_reached"])
            self.assertEqual(result["task"]["status"], "retry-wait")
            self.assertTrue(result["task"]["next_eligible_at"])

    def test_nonurgent_task_starvation_rotates_after_two_selections(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state_dir = self.init_campaign(Path(temporary))
            state = json.loads((state_dir / "campaign-state.json").read_text(encoding="utf-8"))
            state["engagement_scaling"]["base_actions_used"] = 100
            state["dispatcher"]["last_selected_task_type"] = "analytics-and-investigation"
            state["dispatcher"]["consecutive_same_task_type"] = 2
            write_json(state_dir / "campaign-state.json", state)
            queue = json.loads((state_dir / "work-queue.json").read_text(encoding="utf-8"))
            queue["items"].extend(
                [
                    {"task_id": "analytics-first", "task_type": "analytics-and-investigation", "lane": "offline", "priority": 8, "status": "pending", "ready": True, "requires_linkedin": False},
                    {"task_id": "creator-alternative", "task_type": "creator-research", "lane": "offline", "priority": 9, "status": "pending", "ready": True, "requires_linkedin": False},
                ]
            )
            write_json(state_dir / "work-queue.json", queue)
            decision = run_json(
                ["python3", str(ORCHESTRATOR / "dispatch_next_work.py"), str(state_dir)]
            )
            self.assertEqual(decision["task"]["task_id"], "creator-alternative")


if __name__ == "__main__":
    unittest.main()
