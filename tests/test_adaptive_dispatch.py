#!/usr/bin/env python3
"""Contract tests for the v6 rolling campaign runtime."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "linkedin-campaign-operator-v3"
ORCHESTRATOR = PLUGIN / "skills" / "linkedin-campaign-orchestrator" / "scripts"
PLANNING = PLUGIN / "skills" / "linkedin-engagement-planning" / "scripts"
EXECUTION = PLUGIN / "skills" / "linkedin-engagement-execution" / "scripts"
DISCOVERY = PLUGIN / "skills" / "linkedin-opportunity-discovery" / "scripts"
REGIONAL = PLUGIN / "skills" / "linkedin-regional-intelligence" / "scripts"
PUBLISHING = PLUGIN / "skills" / "linkedin-publishing-operations" / "scripts"
REPAIR = PLUGIN / "skills" / "linkedin-runtime-repair" / "scripts"
NOW = datetime(2026, 8, 25, 12, 0, tzinfo=ZoneInfo("Asia/Kolkata"))


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, values: list[dict]) -> None:
    path.write_text("".join(json.dumps(value) + "\n" for value in values), encoding="utf-8")


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def run_json(*arguments: object, check: bool = True) -> tuple[subprocess.CompletedProcess[str], dict]:
    completed = subprocess.run(
        [str(argument) for argument in arguments], check=False, capture_output=True, text=True
    )
    if check and completed.returncode:
        raise AssertionError(
            f"command failed: {arguments}\nstdout={completed.stdout}\nstderr={completed.stderr}"
        )
    raw = completed.stdout if completed.stdout.strip() else completed.stderr
    return completed, json.loads(raw)


def initialize(state_dir: Path, now: datetime = NOW) -> None:
    run_json(
        "python3", ORCHESTRATOR / "init_campaign.py", state_dir,
        "--campaign-id", "v6-test", "--owner-name", "Test Operator",
        "--profile-url", "https://www.linkedin.com/in/test-operator/",
    )
    run_json(
        "python3", ORCHESTRATOR / "runtime_control.py", state_dir,
        "--now", now.isoformat(), "consent-grant",
    )
    executor = read_json(state_dir / "external-executor.json")
    executor.update({
        "mode": "test-fixture",
        "test_fixture": True,
        "status": "active",
        "unattended": True,
        "interactive_fallback_enabled": False,
        "declared_scopes": ["w_member_social", "r_member_social"],
        "supported_action_classes": ["publication", "comment", "reply", "reaction"],
        "verification": {
            "status": "passed",
            "identity_verified": True,
            "verified_at": now.isoformat(),
            "verified_actor_urn": "urn:li:person:test-operator",
            "write_scope_verified": True,
            "read_scope_verified": True,
        },
    })
    write_json(state_dir / "external-executor.json", executor)
    day = now.astimezone(ZoneInfo("Asia/Kolkata")).date().isoformat()
    ledger = read_json(state_dir / "stage-ledger.json")
    ledger.setdefault("stages", []).append({
        "stage_id": f"preflight-{day}", "stage_type": "preflight", "status": "completed",
        "required_artifacts": [], "completed_artifacts": [], "content_day_local": day,
    })
    write_json(state_dir / "stage-ledger.json", ledger)


def package(index: int, *, status: str = "ready") -> dict:
    regions = ["india", "us", "india", "us", "uk-eu", "apac"]
    pillars = ["agents", "security", "data", "product", "agents", "security"]
    formats = ["carousel", "gif", "single-image", "carousel", "gif", "single-image"]
    stages = (
        "research_brief", "claim_verification", "caption", "asset", "watermark",
        "validation", "publication_decision",
    )
    return {
        "package_id": f"pkg-{index}", "post_id": f"post-{index}", "status": status,
        "ready": status in {"ready", "validated"}, "publication_kind": "normal",
        "region": regions[index], "topic": f"topic-{index}", "angle": f"angle-{index}",
        "content_pillar": pillars[index], "format_treatment": formats[index],
        "freshness_expiry": (NOW + timedelta(days=2)).isoformat(),
        "stages": {name: True for name in stages},
    }


def seed_pipeline(state_dir: Path) -> None:
    pipeline = read_json(state_dir / "content-pipeline.json")
    pipeline["topic_candidates"] = [{
        "topic_id": f"topic-{index}", "region": "india" if index % 2 == 0 else "us",
        "demographic_hypothesis": "technical leaders",
        "freshness_expiry": (NOW + timedelta(days=2)).isoformat(),
        "portfolio_role": "proven" if index < 8 else "exploration",
        "competing_angle": f"competing-{index}",
        "intended_growth_outcome": "qualified profile views",
    } for index in range(12)]
    pipeline["briefs"] = [
        {"brief_id": f"brief-{index}", "topic_id": f"topic-{index}"} for index in range(6)
    ]
    pipeline["packages"] = [package(index) for index in range(6)]
    pipeline["analytics_schedule"] = []
    write_json(state_dir / "content-pipeline.json", pipeline)


def opportunity(index: int, **overrides: object) -> dict:
    value = {
        "candidate_id": f"candidate-{index}", "candidate_identity": f"person-{index}",
        "post_id": f"candidate-post-{index}", "lane": "proactive", "status": "qualified",
        "action_type": "comment", "action_available": True, "score": 70,
        "target_status": "new", "follower_count": 5000, "cooldown_passed": True,
        "proactive_actions_person_7d": 0,
        "expires_at": (NOW + timedelta(hours=12)).isoformat(),
        "evidence": {"post_url": f"https://www.linkedin.com/feed/update/{index}"},
    }
    value.update(overrides)
    return value


class V6RuntimeTests(unittest.TestCase):
    def make_campaign(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temporary = tempfile.TemporaryDirectory()
        state_dir = Path(temporary.name) / "campaign"
        initialize(state_dir)
        return temporary, state_dir

    def test_initialization_and_migration_contract_validate(self) -> None:
        temporary, state_dir = self.make_campaign()
        self.addCleanup(temporary.cleanup)
        config = read_json(state_dir / "campaign-config.json")
        config["runtime_repair"].update({"codex_fallback": True, "codex_scope": "legacy"})
        config["automation_reliability"]["browser_binding"]["routine_device_questions_allowed"] = False
        write_json(state_dir / "campaign-config.json", config)
        state = read_json(state_dir / "campaign-state.json")
        state["autonomous_execution"]["zero_human_ready"] = False
        state["autonomous_execution"]["observer_input_required"] = False
        state["dispatcher"]["continuation"]["owner_input_required"] = False
        write_json(state_dir / "campaign-state.json", state)
        consent = read_json(state_dir / "consent-record.json")
        consent["approved_action_classes"] = consent.pop("configured_action_classes")
        consent["authorization_receipt"] = consent.pop("operating_receipt")
        write_json(state_dir / "consent-record.json", consent)
        executor = read_json(state_dir / "external-executor.json")
        executor["zero_human"] = executor.pop("unattended")
        executor["observer_input_required"] = False
        write_json(state_dir / "external-executor.json", executor)
        queue = read_json(state_dir / "work-queue.json")
        queue["items"] = [{
            "task_id": "legacy-contract",
            "task_type": "analytics-and-investigation",
            "status": "pending",
            "execution_authorization": {"decision": "execute"},
        }]
        write_json(state_dir / "work-queue.json", queue)
        _, migration = run_json(
            "python3", ORCHESTRATOR / "migrate_campaign.py", state_dir, "--now", NOW.isoformat()
        )
        self.assertEqual(migration["schema_version"], "2.0")
        _, validation = run_json("python3", ORCHESTRATOR / "validate_campaign.py", state_dir)
        self.assertTrue(validation["valid"])
        self.assertEqual(
            read_json(state_dir / "campaign-config.json")["autonomous_execution"]["mode"],
            "unattended-official-api",
        )
        migrated_config = read_json(state_dir / "campaign-config.json")
        self.assertNotIn("codex_fallback", migrated_config["runtime_repair"])
        self.assertTrue(
            migrated_config["automation_reliability"]["browser_binding"]["direct_pinned_device_selection"]
        )
        migrated_state = read_json(state_dir / "campaign-state.json")
        self.assertNotIn("zero_human_ready", migrated_state["autonomous_execution"])
        self.assertNotIn("observer_input_required", migrated_state["autonomous_execution"])
        migrated_consent = read_json(state_dir / "consent-record.json")
        self.assertIn("configured_action_classes", migrated_consent)
        self.assertNotIn("approved_action_classes", migrated_consent)
        self.assertIn("operating_receipt", migrated_consent)
        migrated_executor = read_json(state_dir / "external-executor.json")
        self.assertIn("unattended", migrated_executor)
        self.assertNotIn("zero_human", migrated_executor)
        migrated_queue = read_json(state_dir / "work-queue.json")
        self.assertIn("dispatch_contract", migrated_queue["items"][0])
        self.assertNotIn("execution_authorization", migrated_queue["items"][0])
        for name in (
            "operational-output.json", "content-pipeline.json", "regional-performance.json",
            "repair-state.json", "repair-events.jsonl",
        ):
            self.assertTrue((state_dir / name).exists(), name)

    def test_rolling_output_uses_canonical_evidence_across_rollover(self) -> None:
        temporary, state_dir = self.make_campaign()
        self.addCleanup(temporary.cleanup)
        recent, old = NOW - timedelta(hours=1), NOW - timedelta(hours=25)
        actions = [{
            "action_id": f"a-{index}", "lane": "proactive", "executed_at": recent.isoformat(),
            "confirmed": True, "external_action_occurred": True,
        } for index in range(160)]
        actions += [{
            "action_id": f"old-{index}", "lane": "proactive", "executed_at": old.isoformat(),
            "confirmed": True,
        } for index in range(20)]
        actions += [{
            "action_id": f"reply-{index}", "lane": "direct-inbound",
            "executed_at": recent.isoformat(), "confirmed": True,
        } for index in range(3)]
        actions.append(dict(actions[0]))
        write_jsonl(state_dir / "interaction-log.jsonl", actions)
        write_jsonl(state_dir / "publication-evidence.jsonl", [{
            "post_id": f"p-{index}", "published_at": (NOW - timedelta(hours=index * 2)).isoformat(),
            "verified": True,
        } for index in range(6)])
        _, result = run_json(
            "python3", ORCHESTRATOR / "operational_output.py", state_dir, "--now", NOW.isoformat()
        )
        self.assertEqual(result["actions"]["rolling_24h_actions"], 160)
        self.assertEqual(result["actions"]["direct_inbound_replies"], 3)
        self.assertEqual(result["actions"]["checkpoints_reached"], [40, 80, 120, 160])
        self.assertEqual(result["publishing"]["rolling_24h_posts"], 6)

    def test_action_cap_blocks_counted_work_but_not_inbound(self) -> None:
        temporary, state_dir = self.make_campaign()
        self.addCleanup(temporary.cleanup)
        write_jsonl(state_dir / "interaction-log.jsonl", [{
            "action_id": f"cap-{index}", "lane": "proactive",
            "executed_at": (NOW - timedelta(minutes=5)).isoformat(), "confirmed": True,
        } for index in range(200)])
        action_path = Path(temporary.name) / "action.json"
        base = {
            "action_id": "blocked-201", "lane": "proactive", "action_type": "comment",
            "triggering_signal": "qualified-post", "scheduling_rationale": "highest score",
            "relationship_strength": 0.3,
        }
        write_json(action_path, base)
        completed, result = run_json(
            "python3", PLANNING / "record_action.py", state_dir, action_path,
            "--now", NOW.isoformat(), check=False,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertFalse(result["valid"])
        base.update({
            "action_id": "inbound-over-cap", "lane": "direct-inbound", "action_type": "reply",
            "triggering_signal": "genuine-comment", "scheduling_rationale": "direct response",
        })
        write_json(action_path, base)
        _, accepted = run_json(
            "python3", PLANNING / "record_action.py", state_dir, action_path, "--now", NOW.isoformat()
        )
        self.assertEqual(accepted["rolling_24h_actions"], 200)
        self.assertEqual(accepted["direct_inbound_replies"], 1)
        self.assertEqual(accepted["budget_class"], "direct-inbound-outside-cap")

    def test_proactive_dm_requires_relationship(self) -> None:
        temporary, state_dir = self.make_campaign()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / "dm.json"
        action = {
            "action_id": "dm-1", "lane": "proactive", "action_type": "dm",
            "triggering_signal": "relationship-opportunity",
            "scheduling_rationale": "relevant follow-up", "relationship_strength": 0.8,
        }
        write_json(path, action)
        completed, rejected = run_json(
            "python3", PLANNING / "record_action.py", state_dir, path,
            "--now", NOW.isoformat(), check=False,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("existing connection", rejected["error"])
        action.update({
            "connection_status": "connected", "prior_interaction_evidence": {"action_id": "earlier"}
        })
        write_json(path, action)
        _, accepted = run_json(
            "python3", PLANNING / "record_action.py", state_dir, path, "--now", NOW.isoformat()
        )
        self.assertTrue(accepted["valid"])

    def test_discovery_upsert_and_ten_action_burst_cap(self) -> None:
        temporary, state_dir = self.make_campaign()
        self.addCleanup(temporary.cleanup)
        discoveries = Path(temporary.name) / "discoveries.json"
        write_json(discoveries, {
            "source": "own-post-signals", "opportunities": [opportunity(index) for index in range(15)]
        })
        _, upserted = run_json(
            "python3", DISCOVERY / "upsert_opportunities.py", state_dir, discoveries,
            "--now", NOW.isoformat(),
        )
        self.assertEqual(upserted["canonical_eligible_count"], 15)
        canonical = read_json(state_dir / "engagement-opportunities.json")
        self.assertEqual(canonical["count_source"], "canonical-records")
        self.assertTrue(all(item.get("candidate_id") for item in canonical["opportunities"]))
        _, burst = run_json(
            "python3", EXECUTION / "build_burst.py", state_dir, "--now", NOW.isoformat()
        )
        self.assertEqual(burst["task"]["action_count"], 10)

    def test_one_candidate_executes_before_discovery(self) -> None:
        temporary, state_dir = self.make_campaign()
        self.addCleanup(temporary.cleanup)
        write_json(state_dir / "engagement-opportunities.json", {
            "schema_version": "2.0", "campaign_id": "v6-test", "opportunities": [opportunity(1)]
        })
        _, decision = run_json(
            "python3", ORCHESTRATOR / "dispatch_next_work.py", state_dir,
            "--now", NOW.isoformat(), "--record"
        )
        self.assertEqual(decision["task"]["task_type"], "engagement-burst-execution")
        self.assertEqual(decision["task"]["action_count"], 1)

    def test_stale_counter_cannot_override_canonical_queue(self) -> None:
        temporary, state_dir = self.make_campaign()
        self.addCleanup(temporary.cleanup)
        state = read_json(state_dir / "campaign-state.json")
        state["engagement_scaling"]["adaptive_reserve"]["qualified_count"] = 99
        write_json(state_dir / "campaign-state.json", state)
        write_json(state_dir / "engagement-opportunities.json", {
            "schema_version": "2.0", "campaign_id": "v6-test", "opportunities": []
        })
        _, decision = run_json(
            "python3", ORCHESTRATOR / "dispatch_next_work.py", state_dir,
            "--now", NOW.isoformat(), "--record"
        )
        self.assertEqual(decision["task"]["task_type"], "opportunity-discovery")
        state = read_json(state_dir / "campaign-state.json")
        reserve = state["engagement_scaling"]["adaptive_reserve"]
        self.assertEqual(reserve["qualified_count"], 0)
        self.assertEqual(reserve["target_count"], 40)

    def test_low_yield_source_backoff_rotates_immediately(self) -> None:
        temporary, state_dir = self.make_campaign()
        self.addCleanup(temporary.cleanup)
        discoveries = Path(temporary.name) / "empty.json"
        write_json(discoveries, {
            "source": "direct-inbound-and-notifications", "opportunities": []
        })
        _, result = run_json(
            "python3", DISCOVERY / "upsert_opportunities.py", state_dir, discoveries,
            "--now", NOW.isoformat(),
        )
        self.assertIsNotNone(result["backoff_until"])
        _, decision = run_json(
            "python3", ORCHESTRATOR / "dispatch_next_work.py", state_dir, "--now", NOW.isoformat()
        )
        self.assertEqual(decision["task"]["task_type"], "opportunity-discovery")
        self.assertNotEqual(
            decision["task"]["discovery_source"], "direct-inbound-and-notifications"
        )

    def test_retry_wait_discovery_source_cannot_spawn_duplicate(self) -> None:
        temporary, state_dir = self.make_campaign()
        self.addCleanup(temporary.cleanup)
        queue = read_json(state_dir / "work-queue.json")
        queue["items"].append({
            "task_id": "generate-opportunities-existing-targets",
            "task_type": "opportunity-discovery",
            "lane": "linkedin",
            "status": "retry-wait",
            "ready": False,
            "requires_linkedin": True,
            "discovery_source": "existing-targets-and-hubs",
            "next_eligible_at": (NOW + timedelta(minutes=30)).isoformat(),
        })
        write_json(state_dir / "work-queue.json", queue)
        _, decision = run_json(
            "python3", ORCHESTRATOR / "dispatch_next_work.py", state_dir,
            "--now", NOW.isoformat(),
        )
        self.assertEqual(decision["task"]["task_type"], "opportunity-discovery")
        self.assertNotEqual(decision["task"]["discovery_source"], "existing-targets-and-hubs")

    def test_all_backed_off_sources_do_not_spawn_discovery(self) -> None:
        temporary, state_dir = self.make_campaign()
        self.addCleanup(temporary.cleanup)
        module_path = ORCHESTRATOR / "opportunity_recovery.py"
        spec = importlib.util.spec_from_file_location("v6_source_backoff", module_path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        state = {"opportunity_recovery": {"source_performance": {
            source: {"backoff_until": (NOW + timedelta(minutes=30)).isoformat()}
            for source in module.DEFAULT_SOURCES
        }}}
        self.assertIsNone(module.next_discovery_source(state, {}, NOW))

    def test_recovery_tiers_and_weekly_limit_are_locked(self) -> None:
        module_path = ORCHESTRATOR / "opportunity_recovery.py"
        spec = importlib.util.spec_from_file_location("v6_opportunity_recovery", module_path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        expected = {
            "normal": (65, 3000, 72), "expansion": (60, 2000, 48),
            "intensive": (55, 1000, 24),
        }
        for mode, locked in expected.items():
            state = {"opportunity_recovery": {"mode": mode}, "engagement_scaling": {}}
            _, gate = module.active_tier(state, {"opportunity_recovery": {}})
            self.assertEqual(
                (gate["minimum_score"], gate["new_target_min_followers"], gate["cooldown_hours"]),
                locked,
            )
            candidate = opportunity(1, score=locked[0], follower_count=locked[1])
            self.assertEqual(len(module.eligible_opportunities(
                {"opportunities": [candidate]}, state, {"opportunity_recovery": {}}, NOW
            )), 1)
            candidate["proactive_actions_person_7d"] = 2
            self.assertEqual(module.eligible_opportunities(
                {"opportunities": [candidate]}, state, {"opportunity_recovery": {}}, NOW
            ), [])

    def test_six_package_inventory_enforces_diversity(self) -> None:
        temporary, state_dir = self.make_campaign()
        self.addCleanup(temporary.cleanup)
        seed_pipeline(state_dir)
        _, valid = run_json(
            "python3", PUBLISHING / "publishing_ledger.py", state_dir, "--now", NOW.isoformat()
        )
        self.assertEqual(valid["validated_unpublished_packages"], 6)
        self.assertEqual(valid["portfolio_errors"], [])
        pipeline = read_json(state_dir / "content-pipeline.json")
        pipeline["packages"][1]["format_treatment"] = pipeline["packages"][0]["format_treatment"]
        write_json(state_dir / "content-pipeline.json", pipeline)
        _, invalid = run_json(
            "python3", PUBLISHING / "publishing_ledger.py", state_dir, "--now", NOW.isoformat()
        )
        self.assertIn("consecutive packages repeat format_treatment", invalid["portfolio_errors"])

    def test_timing_uses_six_posts_and_spacing_floor(self) -> None:
        temporary, state_dir = self.make_campaign()
        self.addCleanup(temporary.cleanup)
        posts = [package(index) for index in range(6)]
        for post in posts:
            post["published"] = False
        components = {
            "regional_activity": 0.9, "qualified_target_activity": 0.9,
            "topic_freshness": 0.9, "network_velocity": 0.9,
            "previous_post_engagement_velocity": 0.9, "historical_equal_age": 0.9,
            "format_pillar_fit": 0.9, "remaining_day_opportunity": 0.9,
        }
        path = Path(temporary.name) / "timing.json"
        write_json(path, {"posts": posts, "opportunities": [{"post_id": "post-0", **components}]})
        _, selected = run_json("python3", ORCHESTRATOR / "select_publish_time.py", path)
        self.assertEqual(selected["decision"], "publish-now")
        posts[0]["published"] = True
        write_json(path, {"posts": posts, "opportunities": [{
            "post_id": "post-1", "minutes_since_previous_publication": 119, **components
        }]})
        _, deferred = run_json("python3", ORCHESTRATOR / "select_publish_time.py", path)
        self.assertEqual(deferred["decision"], "continue-investigation")

    def test_ready_package_requires_scored_decision_before_live_execution(self) -> None:
        temporary, state_dir = self.make_campaign()
        self.addCleanup(temporary.cleanup)
        seed_pipeline(state_dir)
        _, evaluation = run_json(
            "python3", ORCHESTRATOR / "dispatch_next_work.py", state_dir,
            "--now", NOW.isoformat(), "--record",
        )
        self.assertEqual(evaluation["task"]["task_type"], "rolling-output-evaluation")
        self.assertEqual(evaluation["task"]["package_id"], "pkg-0")
        payload = json.dumps({
            "decision": "publish-now", "opportunity_score": 82,
            "selected_at": NOW.isoformat(), "evidence": {"regional_activity": 0.91},
        })
        run_json(
            "python3", ORCHESTRATOR / "runtime_control.py", state_dir,
            "--now", NOW.isoformat(), "task-event", "--task-id", evaluation["task"]["task_id"],
            "--event", "complete", "--payload", payload,
        )
        pipeline = read_json(state_dir / "content-pipeline.json")
        self.assertEqual(pipeline["packages"][0]["publication_decision"]["decision"], "publish-now")
        _, next_decision = run_json(
            "python3", ORCHESTRATOR / "dispatch_next_work.py", state_dir,
            "--now", (NOW + timedelta(minutes=1)).isoformat(),
        )
        self.assertEqual(next_decision["task"]["task_type"], "publication-queue-building")

    def test_six_publications_schedule_four_analytics_checkpoints_each(self) -> None:
        temporary, state_dir = self.make_campaign()
        self.addCleanup(temporary.cleanup)
        seed_pipeline(state_dir)
        start = NOW - timedelta(hours=10)
        for index in range(6):
            when = start + timedelta(hours=index * 2)
            evidence = Path(temporary.name) / f"evidence-{index}.json"
            write_json(evidence, {
                "package_id": f"pkg-{index}", "post_id": f"live-{index}",
                "post_url": f"https://www.linkedin.com/feed/update/live-{index}",
                "verified": True, "published_at": when.isoformat(),
            })
            _, result = run_json(
                "python3", PUBLISHING / "publishing_ledger.py", state_dir,
                "--now", when.isoformat(), "--record-publication", evidence,
            )
        self.assertEqual(result["rolling_24h_posts"], 6)
        self.assertEqual(result["post_debt"], 0)
        pipeline = read_json(state_dir / "content-pipeline.json")
        self.assertEqual(len(pipeline["analytics_schedule"]), 24)
        for post_id in {item["post_id"] for item in pipeline["analytics_schedule"]}:
            offsets = {item["checkpoint_minutes"] for item in pipeline["analytics_schedule"] if item["post_id"] == post_id}
            self.assertEqual(offsets, {30, 120, 360, 1440})
        _, inventory = run_json(
            "python3", PUBLISHING / "publishing_ledger.py", state_dir,
            "--now", NOW.isoformat(), "--record",
        )
        self.assertEqual(inventory["inventory_debt"], 6)

    def test_eight_post_cap_is_hard(self) -> None:
        temporary, state_dir = self.make_campaign()
        self.addCleanup(temporary.cleanup)
        seed_pipeline(state_dir)
        start = NOW - timedelta(hours=14)
        for index in range(8):
            when = start + timedelta(hours=index * 2)
            evidence = Path(temporary.name) / f"cap-{index}.json"
            write_json(evidence, {
                "post_id": f"cap-{index}", "verified": True, "published_at": when.isoformat()
            })
            run_json(
                "python3", PUBLISHING / "publishing_ledger.py", state_dir,
                "--now", when.isoformat(), "--record-publication", evidence,
            )
        ninth = Path(temporary.name) / "ninth.json"
        write_json(ninth, {
            "post_id": "ninth", "verified": True,
            "published_at": (NOW + timedelta(hours=2)).isoformat(),
        })
        completed, result = run_json(
            "python3", PUBLISHING / "publishing_ledger.py", state_dir,
            "--now", (NOW + timedelta(hours=2)).isoformat(),
            "--record-publication", ninth, check=False,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("cap", result["error"])

    def test_regional_bootstrap_then_evidence_allocation(self) -> None:
        temporary, state_dir = self.make_campaign()
        self.addCleanup(temporary.cleanup)
        _, bootstrap = run_json("python3", REGIONAL / "allocate_regions.py", state_dir)
        self.assertEqual(
            bootstrap["six_post_allocation"], ["india", "india", "us", "us", "uk-eu", "apac"]
        )
        regional = read_json(state_dir / "regional-performance.json")
        regional["observations"] = [{
            "region": ["india", "us", "uk-eu", "apac"][index % 4],
            "performance_score": 60 + index,
        } for index in range(12)]
        write_json(state_dir / "regional-performance.json", regional)
        _, adaptive = run_json("python3", REGIONAL / "allocate_regions.py", state_dir, "--record")
        self.assertEqual(adaptive["mode"], "evidence-adaptive-4-core-2-exploration")
        self.assertEqual(len(adaptive["six_post_allocation"]), 6)
        self.assertIn("india", adaptive["six_post_allocation"])
        self.assertIn("us", adaptive["six_post_allocation"])

    def test_auditor_recovers_missing_package_and_analytics_work(self) -> None:
        temporary, state_dir = self.make_campaign()
        self.addCleanup(temporary.cleanup)
        seed_pipeline(state_dir)
        pipeline = read_json(state_dir / "content-pipeline.json")
        pipeline["packages"][0]["stages"]["watermark"] = False
        pipeline["packages"][1]["status"] = "published"
        pipeline["packages"][1]["post_id"] = "published-without-schedule"
        write_json(state_dir / "content-pipeline.json", pipeline)
        _, audit = run_json(
            "python3", ORCHESTRATOR / "audit_pipeline.py", state_dir,
            "--now", NOW.isoformat(), "--write",
        )
        types = {item["task_type"] for item in audit["recovery_tasks"]}
        self.assertIn("six-package-replenishment", types)
        self.assertIn("scheduled-analytics-snapshot", types)
        self.assertEqual(
            read_json(state_dir / "content-pipeline.json")["packages"][0]["status"],
            "needs-v6-revalidation",
        )

    def test_publication_task_completion_uses_v6_canonical_ledger(self) -> None:
        temporary, state_dir = self.make_campaign()
        self.addCleanup(temporary.cleanup)
        seed_pipeline(state_dir)
        queue = read_json(state_dir / "work-queue.json")
        queue["items"] = [{
            "task_id": "publish-pkg-0", "task_type": "publication-execution",
            "status": "running", "ready": True, "lane": "linkedin",
            "requires_linkedin": True, "package_id": "pkg-0", "region": "india",
            "publication_kind": "normal",
        }]
        write_json(state_dir / "work-queue.json", queue)
        payload = json.dumps({
            "post_id": "canonical-live-post", "post_url": "https://www.linkedin.com/feed/update/live",
            "verified": True, "published_at": NOW.isoformat(),
        })
        _, completed = run_json(
            "python3", ORCHESTRATOR / "runtime_control.py", state_dir,
            "--now", NOW.isoformat(), "task-event", "--task-id", "publish-pkg-0",
            "--event", "complete", "--payload", payload,
        )
        self.assertEqual(completed["task"]["publication_result"]["rolling_24h_posts"], 1)
        evidence = [
            json.loads(line) for line in (state_dir / "publication-evidence.jsonl").read_text().splitlines()
            if line.strip()
        ]
        self.assertEqual([item["post_id"] for item in evidence], ["canonical-live-post"])
        pipeline = read_json(state_dir / "content-pipeline.json")
        published = next(item for item in pipeline["packages"] if item["package_id"] == "pkg-0")
        self.assertEqual(published["status"], "published")
        self.assertEqual(len(pipeline["analytics_schedule"]), 4)

    def test_restart_recovers_lease_without_duplicate_action(self) -> None:
        temporary, state_dir = self.make_campaign()
        self.addCleanup(temporary.cleanup)
        queue = read_json(state_dir / "work-queue.json")
        queue["items"] = [{
            "task_id": "unfinished", "task_type": "six-package-replenishment",
            "status": "leased", "ready": True, "lane": "offline",
            "requires_linkedin": False, "lease_id": "old",
            "lease_expires_at": (NOW + timedelta(hours=1)).isoformat(),
        }]
        write_json(state_dir / "work-queue.json", queue)
        write_jsonl(state_dir / "interaction-log.jsonl", [{
            "action_id": "confirmed-once", "lane": "proactive",
            "executed_at": NOW.isoformat(), "confirmed": True,
        }])
        _, resumed = run_json(
            "python3", ORCHESTRATOR / "resume_campaign.py", state_dir,
            "--now", NOW.isoformat(), "--session-id", "restart-test",
        )
        self.assertTrue(resumed["self_revived"])
        self.assertIn("unfinished", resumed["expired_leases"])
        recovered = next(
            item for item in read_json(state_dir / "work-queue.json")["items"]
            if item["task_id"] == "unfinished"
        )
        self.assertEqual(recovered["status"], "recovering")
        self.assertEqual(
            read_json(state_dir / "operational-output.json")["actions"]["rolling_24h_actions"], 1
        )

    def test_dispatch_embeds_automatic_routine_dispatch_contract(self) -> None:
        temporary, state_dir = self.make_campaign()
        self.addCleanup(temporary.cleanup)
        queue = read_json(state_dir / "work-queue.json")
        queue["items"] = [{
            "task_id": "reply-to-qualified-inbound",
            "task_type": "direct-inbound",
            "action_lane": "direct-inbound",
            "status": "pending",
            "ready": True,
            "lane": "linkedin",
            "requires_linkedin": True,
            "idempotency_key": "reply:qualified-inbound",
        }]
        write_json(state_dir / "work-queue.json", queue)
        _, decision = run_json(
            "python3", ORCHESTRATOR / "dispatch_next_work.py", state_dir,
            "--now", NOW.isoformat(), "--record",
        )
        contract = decision["task"]["dispatch_contract"]
        self.assertEqual(contract["decision"], "execute")
        self.assertEqual(contract["mode"], "unattended-executor")
        self.assertTrue(contract["executor_route_configured"])
        self.assertTrue(contract["routine_transition_is_deterministic"])
        self.assertFalse(contract["status_response_terminal"])
        self.assertIsNotNone(contract["receipt_id"])
        stored = next(
            item for item in read_json(state_dir / "work-queue.json")["items"]
            if item["task_id"] == "reply-to-qualified-inbound"
        )
        self.assertEqual(stored["dispatch_contract"], contract)

    def test_routine_dispatch_requires_active_operating_receipt(self) -> None:
        temporary, state_dir = self.make_campaign()
        self.addCleanup(temporary.cleanup)
        consent = read_json(state_dir / "consent-record.json")
        consent["status"] = "revoked"
        write_json(state_dir / "consent-record.json", consent)
        _, result = run_json(
            "python3", ORCHESTRATOR / "dispatch_contract.py", state_dir,
            "--task-json", json.dumps({
                "task_type": "engagement-burst-execution", "lane": "linkedin",
            }),
        )
        paused = result["dispatch_contract"]
        self.assertEqual(paused["decision"], "pause")
        self.assertTrue(paused["setup_input_required"])

    def test_workflow_choice_prompt_is_rejected_during_automatic_dispatch(self) -> None:
        temporary, state_dir = self.make_campaign()
        self.addCleanup(temporary.cleanup)
        completed, rejected_result = run_json(
            "python3", ORCHESTRATOR / "dispatch_contract.py", state_dir,
            "--task-json", json.dumps({
                "task_type": "engagement-burst-execution", "lane": "linkedin",
            }),
            "--output-text", "The comment is ready. Post this?",
            check=False,
        )
        self.assertEqual(completed.returncode, 2)
        rejected = rejected_result["output_guard"]
        self.assertFalse(rejected["valid"])
        self.assertEqual(
            rejected["required_action"], "enqueue-and-return-to-dispatcher"
        )
        _, accepted_result = run_json(
            "python3", ORCHESTRATOR / "dispatch_contract.py", state_dir,
            "--task-json", json.dumps({
                "task_type": "engagement-burst-execution", "lane": "linkedin",
            }),
            "--output-text", "Comment verified, logged, and dispatcher resumed.",
        )
        accepted = accepted_result["output_guard"]
        self.assertTrue(accepted["valid"])

    def test_ambiguous_external_outcome_pauses_for_reconciliation(self) -> None:
        temporary, state_dir = self.make_campaign()
        self.addCleanup(temporary.cleanup)
        _, result = run_json(
            "python3", ORCHESTRATOR / "dispatch_contract.py", state_dir,
            "--task-json", json.dumps({
                "task_type": "publication-execution",
                "external_outcome": "ambiguous",
            }),
        )
        contract = result["dispatch_contract"]
        self.assertEqual(contract["decision"], "pause")
        self.assertEqual(contract["mode"], "reconcile-before-retry")
        self.assertFalse(contract["setup_input_required"])
        self.assertTrue(contract["routine_transition_is_deterministic"])

    def test_parent_skill_requires_verified_connected_service(self) -> None:
        parent = (PLUGIN / "skills" / "linkedin-campaign-orchestrator" / "SKILL.md").read_text()
        execution = (PLUGIN / "skills" / "linkedin-engagement-execution" / "SKILL.md").read_text()
        self.assertIn("when the service is available", parent)
        self.assertIn("The connected service owns submission and result verification", parent)
        self.assertIn("The connected service owns submission and result verification", execution)
        self.assertNotIn("ACTION_APPROVAL_PACKET", parent)
        self.assertNotIn("supervising observer", execution)

    def test_unconfigured_executor_parks_external_action_and_continues_local_work(self) -> None:
        temporary, state_dir = self.make_campaign()
        self.addCleanup(temporary.cleanup)
        executor = read_json(state_dir / "external-executor.json")
        executor.update({
            "mode": "official-linkedin-api",
            "status": "unconfigured",
            "declared_scopes": [],
            "supported_action_classes": [],
            "verification": {
                "status": "not-run",
                "identity_verified": False,
                "write_scope_verified": False,
                "read_scope_verified": False,
            },
        })
        executor.pop("test_fixture", None)
        write_json(state_dir / "external-executor.json", executor)
        _, result = run_json(
            "python3", ORCHESTRATOR / "dispatch_contract.py", state_dir,
            "--task-json", json.dumps({"task_type": "comment", "action_type": "comment"}),
        )
        contract = result["dispatch_contract"]
        self.assertEqual(contract["decision"], "pause")
        self.assertEqual(contract["mode"], "executor-setup-pending")
        self.assertFalse(contract["setup_input_required"])
        self.assertEqual(
            contract["executor_readiness"]["executor_state"],
            "setup-pending",
        )

    def test_dispatcher_persists_unattended_state_without_leasing_external_task(self) -> None:
        temporary, state_dir = self.make_campaign()
        self.addCleanup(temporary.cleanup)
        executor = read_json(state_dir / "external-executor.json")
        executor.update({
            "mode": "official-linkedin-api",
            "status": "unconfigured",
            "declared_scopes": [],
            "supported_action_classes": [],
            "verification": {
                "status": "not-run",
                "identity_verified": False,
                "write_scope_verified": False,
                "read_scope_verified": False,
            },
        })
        executor.pop("test_fixture", None)
        write_json(state_dir / "external-executor.json", executor)
        queue = read_json(state_dir / "work-queue.json")
        queue["items"] = [{
            "task_id": "external-comment",
            "task_type": "comment",
            "action_type": "comment",
            "status": "pending",
            "ready": True,
            "lane": "linkedin",
            "requires_linkedin": True,
        }]
        write_json(state_dir / "work-queue.json", queue)
        _, decision = run_json(
            "python3", ORCHESTRATOR / "dispatch_next_work.py", state_dir,
            "--now", NOW.isoformat(), "--record",
        )
        self.assertNotEqual(decision.get("task", {}).get("task_id"), "external-comment")
        stored_task = read_json(state_dir / "work-queue.json")["items"][0]
        self.assertEqual(stored_task["status"], "pending")
        runtime = read_json(state_dir / "campaign-state.json")["autonomous_execution"]
        self.assertFalse(runtime["unattended_ready"])
        self.assertIn("executor-status-active", runtime["missing_capabilities"])

    def test_public_adapter_never_covers_messages_connections_or_follows(self) -> None:
        temporary, state_dir = self.make_campaign()
        self.addCleanup(temporary.cleanup)
        for action_type in ("direct-message", "connection-invitation", "follow"):
            _, result = run_json(
                "python3", ORCHESTRATOR / "executor_readiness.py", state_dir,
                "--task-json", json.dumps({"action_type": action_type}),
            )
            readiness = result["readiness"]
            self.assertFalse(readiness["unattended_ready"])
            self.assertFalse(readiness["setup_input_required"])
            self.assertIn(
                f"unsupported-action-class:{action_type}",
                readiness["missing_capabilities"],
            )

    def test_official_executor_builds_supported_api_mutations(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "execute_external_action",
            ORCHESTRATOR / "execute_external_action.py",
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(ORCHESTRATOR))
        try:
            spec.loader.exec_module(module)
        finally:
            sys.path.remove(str(ORCHESTRATOR))
        post_path, post_body = module.request_parts(
            {"action_class": "publication", "text": "Evidence-backed update."},
            "urn:li:person:test",
        )
        self.assertEqual(post_path, "/rest/posts")
        self.assertEqual(post_body["author"], "urn:li:person:test")
        comment_path, comment_body = module.request_parts(
            {
                "action_class": "comment",
                "target_urn": "urn:li:ugcPost:123",
                "object_urn": "urn:li:activity:123",
                "text": "Useful detail.",
            },
            "urn:li:person:test",
        )
        self.assertEqual(comment_path, "/rest/socialActions/urn%3Ali%3AugcPost%3A123/comments")
        self.assertEqual(comment_body["message"]["text"], "Useful detail.")
        reaction_path, reaction_body = module.request_parts(
            {
                "action_class": "reaction",
                "target_urn": "urn:li:activity:123",
                "reaction_type": "INTEREST",
            },
            "urn:li:person:test",
        )
        self.assertEqual(
            reaction_path, "/rest/reactions?actor=urn%3Ali%3Aperson%3Atest"
        )
        self.assertEqual(reaction_body["root"], "urn:li:activity:123")
        self.assertEqual(reaction_body["reactionType"], "INTEREST")

    def test_programmatic_refresh_credentials_satisfy_unattended_availability(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "credential_manager", ORCHESTRATOR / "credential_manager.py"
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        try:
            spec.loader.exec_module(module)
        finally:
            sys.modules.pop(spec.name, None)
        executor = {
            "credential_source": {
                "type": "environment-or-macos-keychain",
                "access_token_env": "LI_ACCESS",
                "actor_urn_env": "LI_ACTOR",
                "client_id_env": "LI_CLIENT",
                "client_secret_env": "LI_SECRET",
                "refresh_token_env": "LI_REFRESH",
            },
            "token_refresh": {"mode": "programmatic"},
            "verification": {},
        }
        availability = module.credential_availability(
            executor,
            {
                "LI_ACTOR": "urn:li:person:test",
                "LI_CLIENT": "client",
                "LI_SECRET": "secret",
                "LI_REFRESH": "refresh",
            },
        )
        self.assertTrue(availability["access_token_resolvable"])
        self.assertTrue(availability["programmatic_refresh_ready"])

    def test_executor_preflight_derives_scope_coverage_without_persisting_secrets(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "executor_preflight", ORCHESTRATOR / "executor_preflight.py"
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(ORCHESTRATOR))
        try:
            spec.loader.exec_module(module)
        finally:
            sys.path.remove(str(ORCHESTRATOR))
        executor = {
            "mode": "official-linkedin-api",
            "status": "unconfigured",
            "unattended": True,
            "interactive_fallback_enabled": False,
            "credential_source": {
                "type": "environment",
                "access_token_env": "LI_ACCESS",
                "actor_urn_env": "LI_ACTOR",
                "client_id_env": "LI_CLIENT",
                "client_secret_env": "LI_SECRET",
                "refresh_token_env": "LI_REFRESH",
            },
            "token_refresh": {"mode": "programmatic"},
            "verification": {},
        }
        report = module.evaluate_preflight(
            executor,
            {
                "autonomous_execution": {
                    "required_action_classes": ["publication", "comment", "reply", "reaction"]
                }
            },
            {"owner": {"display_name": "Test Operator"}},
            environ={
                "LI_ACCESS": "access",
                "LI_ACTOR": "urn:li:person:test",
                "LI_CLIENT": "client",
                "LI_SECRET": "secret",
                "LI_REFRESH": "refresh",
            },
            introspector=lambda token, client, secret: {
                "active": True,
                "status": "active",
                "scope": "w_member_social_feed,r_member_social_feed,openid,profile",
                "expires_at": 1900000000,
                "auth_type": "3L",
            },
            identity_fetcher=lambda token: {
                "actor_urn": "urn:li:person:test",
                "display_name": "Test Operator",
                "source": "fixture",
            },
            now=NOW,
        )
        self.assertTrue(report["unattended_ready"])
        self.assertEqual(
            executor["supported_action_classes"],
            ["comment", "publication", "reaction", "reply"],
        )
        serialized = json.dumps(executor)
        self.assertNotIn(': "access"', serialized)
        self.assertNotIn(': "secret"', serialized)
        self.assertNotIn(': "refresh"', serialized)

    def test_leased_publication_is_enqueued_for_daemon_without_chat_action(self) -> None:
        temporary, state_dir = self.make_campaign()
        self.addCleanup(temporary.cleanup)
        draft_path = state_dir / "logs" / "draft.json"
        asset_path = state_dir / "logs" / "asset.png"
        write_json(draft_path, {"caption": "Canonical validated caption."})
        asset_path.write_bytes(b"fixture-png")
        pipeline = read_json(state_dir / "content-pipeline.json")
        pipeline["packages"] = [{
            "package_id": "pkg-daemon",
            "source_path": "logs/draft.json",
            "asset_path": "logs/asset.png",
            "region": "india",
            "topic": "Reliable agents",
            "publication_decision": {
                "decision": "publish-now",
                "opportunity_score": 72,
            },
        }]
        write_json(state_dir / "content-pipeline.json", pipeline)
        queue = read_json(state_dir / "work-queue.json")
        queue["items"] = [{
            "task_id": "publish-daemon",
            "task_type": "publication-execution",
            "lane": "linkedin",
            "status": "leased",
            "ready": True,
            "requires_linkedin": True,
            "lease_id": "lease-daemon",
            "package_id": "pkg-daemon",
            "region": "india",
            "idempotency_key": "publish:pkg-daemon",
        }]
        write_json(state_dir / "work-queue.json", queue)
        _, result = run_json(
            "python3", ORCHESTRATOR / "enqueue_external_action.py", state_dir,
            "--task-id", "publish-daemon",
        )
        self.assertEqual(result["decision"], "queued-for-autonomous-daemon")
        self.assertEqual(len(result["enqueued"]), 1)
        action = read_json(state_dir / result["enqueued"][0])
        self.assertEqual(action["text"], "Canonical validated caption.")
        self.assertEqual(action["source_lease_id"], "lease-daemon")
        self.assertTrue(Path(action["media_file"]).is_file())

    def test_daemon_stays_idle_with_ready_fixture_and_blocks_without_readiness(self) -> None:
        temporary, state_dir = self.make_campaign()
        self.addCleanup(temporary.cleanup)
        _, idle = run_json(
            "python3", ORCHESTRATOR / "autonomous_executor_daemon.py", state_dir,
            "--once",
        )
        self.assertEqual(idle["decision"], "idle")
        executor = read_json(state_dir / "external-executor.json")
        executor.update({
            "mode": "official-linkedin-api",
            "status": "unconfigured",
            "declared_scopes": [],
            "supported_action_classes": [],
            "verification": {"status": "not-run"},
        })
        executor.pop("test_fixture", None)
        write_json(state_dir / "external-executor.json", executor)
        completed, blocked = run_json(
            "python3", ORCHESTRATOR / "autonomous_executor_daemon.py", state_dir,
            "--once", check=False,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(blocked["decision"], "readiness-blocked")

    def test_runtime_repair_scope_is_persisted_and_dispatched(self) -> None:
        temporary, state_dir = self.make_campaign()
        self.addCleanup(temporary.cleanup)
        evidence = Path(temporary.name) / "failure.json"
        checkpoint = Path(temporary.name) / "checkpoint.json"
        write_json(evidence, {"error": "chrome disconnected"})
        write_json(checkpoint, {"task_id": "burst-1", "external_outcome": "not-observed"})
        _, repair = run_json(
            "python3", REPAIR / "repair_controller.py", state_dir,
            "--capability", "chrome", "--failure-evidence", evidence,
            "--checkpoint", checkpoint, "--now", NOW.isoformat(),
        )
        request = repair["repair_state"]["active_repair"]
        self.assertEqual(request["repair_scope"]["external_execution_route"], "official-api-executor")
        self.assertIn("reload-current-plugin-runtime", request["repair_scope"]["operations"])
        state = read_json(state_dir / "campaign-state.json")
        state["dispatcher"]["linkedin_lane"] = "recovering"
        write_json(state_dir / "campaign-state.json", state)
        _, decision = run_json(
            "python3", ORCHESTRATOR / "dispatch_next_work.py", state_dir,
            "--now", NOW.isoformat(),
        )
        self.assertEqual(decision["task"]["task_type"], "runtime-repair")


if __name__ == "__main__":
    unittest.main()
