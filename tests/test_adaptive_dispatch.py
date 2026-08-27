#!/usr/bin/env python3
"""Contract tests for the v6 rolling campaign runtime."""

from __future__ import annotations

import importlib.util
import json
import subprocess
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
        _, migration = run_json(
            "python3", ORCHESTRATOR / "migrate_campaign.py", state_dir, "--now", NOW.isoformat()
        )
        self.assertEqual(migration["schema_version"], "2.0")
        _, validation = run_json("python3", ORCHESTRATOR / "validate_campaign.py", state_dir)
        self.assertTrue(validation["valid"])
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
        self.assertIn("publish-linkedin-content", request["codex_scope"]["forbidden"])
        self.assertIn(
            "reinstall-currently-approved-plugin-version", request["codex_scope"]["allowed"]
        )
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
