#!/usr/bin/env python3
"""Release-contract tests for the public cross-platform package."""

from __future__ import annotations

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "linkedin-campaign-operator-v3"
SKILLS = PLUGIN / "skills"
PUBLIC_SITE = "https://linkedin-campaign-operator.sunnychandel73.chatgpt.site"


def frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"missing frontmatter: {path}"
    _, raw, _ = text.split("---", 2)
    value = yaml.safe_load(raw)
    assert isinstance(value, dict)
    return value


def test_parent_and_twelve_children_share_the_rc_version() -> None:
    skill_files = sorted(SKILLS.glob("*/SKILL.md"))
    assert len(skill_files) == 13
    parent_text = (SKILLS / "linkedin-campaign-orchestrator" / "SKILL.md").read_text()
    for skill_file in skill_files:
        metadata = frontmatter(skill_file)
        assert metadata["name"] == skill_file.parent.name
        assert metadata["description"]
        assert metadata["metadata"]["version"] == "6.0.0-rc.28"
        if metadata["name"] != "linkedin-campaign-orchestrator":
            assert f"`{metadata['name']}`" in parent_text


def test_claude_and_codex_manifests_are_aligned() -> None:
    claude = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())
    codex = json.loads((PLUGIN / ".codex-plugin" / "plugin.json").read_text())
    assert claude["name"] == codex["name"] == PLUGIN.name
    assert claude["version"] == codex["version"] == "6.0.0-rc.28"
    assert claude["license"] == codex["license"] == "MIT"
    assert claude["homepage"] == codex["homepage"] == PUBLIC_SITE
    assert codex["skills"] == "./skills/"


def test_orchestrator_verifies_profile_and_repairs_capabilities() -> None:
    text = (SKILLS / "linkedin-campaign-orchestrator" / "SKILL.md").read_text()
    assert "Verify the selected profile read-only" in text
    assert "`linkedin-runtime-repair`" in text
    assert "resume the saved task" in text


def test_runtime_classification_is_host_neutral() -> None:
    text = (
        SKILLS
        / "linkedin-campaign-orchestrator"
        / "references"
        / "state-and-recovery.md"
    ).read_text()
    assert "Derive the current state from saved evidence" in text
    assert "Every resume reloads" in text


def test_interactive_host_never_owns_linkedin_write_actions() -> None:
    text = (SKILLS / "linkedin-campaign-orchestrator" / "SKILL.md").read_text()
    reference = (
        SKILLS
        / "linkedin-campaign-orchestrator"
        / "references"
        / "connected-service.md"
    ).read_text()
    assert "Claude Code manages work in the campaign folder" in text
    assert "Claude Code does not directly change LinkedIn" in text
    assert "The connected service owns submission and result verification" in text
    assert "The connected service handles supported account activity" in reference
    assert "Do not use browser interaction as a replacement" in reference


def test_routine_user_updates_use_plain_language() -> None:
    text = (SKILLS / "linkedin-campaign-orchestrator" / "SKILL.md").read_text()
    assert "## Communication" in text
    assert "Use short, plain progress updates" in text
    assert "Keep filenames, queue mechanics, and recovery details internal" in text
    assert "the one next recovery step" in text
    assert "service unavailable; prepared work saved; next check scheduled" in text
    assert "Keep credential names and service implementation details internal" in text
    assert "routine campaign progress does not require an owner reply" in text


def test_model_context_uses_compact_current_evidence_only() -> None:
    text = (SKILLS / "linkedin-campaign-orchestrator" / "SKILL.md").read_text()
    assert "Treat the compact result from `campaign_cycle.py` as the model-facing control surface" in text
    assert "Do not paste raw configuration files" in text
    assert "It does not reproduce prior chat history" in text
    assert "claims that an agreement occurred when no durable record proves it" in text
    assert "project only the available local task" in text


def test_public_descriptions_are_plain_language() -> None:
    marketplace = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text())
    claude = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())
    codex = json.loads((PLUGIN / ".codex-plugin" / "plugin.json").read_text())
    descriptions = [
        marketplace["description"],
        marketplace["plugins"][0]["description"],
        claude["description"],
        codex["description"],
        codex["interface"]["shortDescription"],
        codex["interface"]["longDescription"],
        *(frontmatter(path)["description"] for path in sorted(SKILLS.glob("*/SKILL.md"))),
    ]
    internal_terms = {
        "160",
        "200",
        "daemon",
        "dispatcher",
        "idempotency",
        "lease",
        "mutation",
        "oauth",
        "outbox",
        "launchagent",
    }
    for description in descriptions:
        lowered = description.lower()
        assert not any(term in lowered for term in internal_terms), description


def test_claude_runtime_has_no_codex_dependency() -> None:
    runtime_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in SKILLS.rglob("*")
        if path.is_file() and path.suffix in {".md", ".py", ".json"}
    )
    assert "Codex" not in runtime_text
    assert "invoke-codex" not in runtime_text.lower()


def test_continuation_never_becomes_an_owner_choice() -> None:
    text = (SKILLS / "linkedin-campaign-orchestrator" / "SKILL.md").read_text()
    assert "Maintain exactly one recurring campaign continuation" in text
    assert "never create a duplicate" in text
    assert "owner_reply_required: false" in text
    assert "create one persistent claude desktop routine" in text.lower()
    assert "host-native-recurring-task" in text
    assert "must survive the current Claude session" in text
    assert "A session cron or in-session loop does not satisfy this contract" in text
    assert "Do not call scheduled-task create or update" in text
    assert "run `continuation_due.py` first" in text


def test_routine_setup_is_resolved_without_optional_owner_questions() -> None:
    text = (SKILLS / "linkedin-campaign-orchestrator" / "SKILL.md").read_text()
    assert "Resolve routine setup choices directly" in text
    assert "the only device matching the current host platform" in text
    assert "the device marked local or current" in text
    assert "Routine device IDs are resolved by this order" in text
    assert "browser-bind --device-id DEVICE_ID" in text
    assert "Pass that device ID directly to the browser tab and navigation calls" in text
    assert "connected-browser discovery is unnecessary when an ID is already available" in text
    assert "profile_verification" in text
    assert "--browser-device-id DEVICE_ID" in text
    assert "use the packaged template defaults" in text
    assert "`unavailable` is a complete setup result" in text
    assert "Optional preferences stay at saved defaults" in text
    assert "scope_confirmation_required: false" in text
    assert "never expand into future account changes" in text


def test_orchestrator_uses_deterministic_plugin_path_resolution() -> None:
    text = (SKILLS / "linkedin-campaign-orchestrator" / "SKILL.md").read_text()
    assert "Resolve the newest installed plugin" in text
    assert "scripts/resolve_latest_plugin.py" in text
    assert "Load the returned parent skill and each child skill needed" in text


def test_orchestrator_uses_one_deterministic_campaign_cycle() -> None:
    text = (SKILLS / "linkedin-campaign-orchestrator" / "SKILL.md").read_text()
    assert "scripts/campaign_cycle.py STATE_DIR --session-start" in text
    assert "Follow the returned `next_action` exactly" in text
    assert "Run the exact command returned in `after_save` immediately" in text
    assert "do not answer with a terminal status while it returns executable work" in text
    assert "completion_command_template" in text
    assert "do not edit queue or stage status directly" in text


def test_content_completion_uses_task_inventory_targets() -> None:
    text = (SKILLS / "linkedin-content-production" / "SKILL.md").read_text()
    assert "read `topic_candidate_target` and `required_package_count`" in text
    assert "before running the completion command" in text
    assert "returns the exact missing counts" in text


def test_campaign_pacing_is_configured_and_routes_are_explicit() -> None:
    text = (SKILLS / "linkedin-campaign-orchestrator" / "SKILL.md").read_text()
    assert "Use the campaign configuration for quantity, pacing, inventory" in text
    assert "Do not invent activity to satisfy a numeric target" in text
    assert "create one checked local request" in text
    for child in (
        "linkedin-opportunity-discovery",
        "linkedin-engagement-execution",
        "linkedin-regional-intelligence",
        "linkedin-publishing-operations",
        "linkedin-runtime-repair",
    ):
        assert f"`{child}`" in text


def test_model_facing_instructions_avoid_the_failed_runtime_language() -> None:
    model_facing = "\n".join(
        path.read_text(encoding="utf-8")
        for path in SKILLS.rglob("*.md")
    ).lower()
    failed_phrases = {
        "autonomous executor",
        "unattended executor",
        "outbox daemon",
        "macos keychain",
        "oauth credential",
        "rolling 160-action",
        "target 160",
        "cap at 200",
        "six-to-eight",
        "blanket consent",
        "without your review",
        "without active supervision",
    }
    assert not any(phrase in model_facing for phrase in failed_phrases)
    assert not (
        SKILLS
        / "linkedin-campaign-orchestrator"
        / "references"
        / "autonomous-execution.md"
    ).exists()


def test_startup_script_surface_excludes_service_provisioning_implementations() -> None:
    scripts = SKILLS / "linkedin-campaign-orchestrator" / "scripts"
    denied = {
        "autonomous_executor_daemon.py",
        "bootstrap_executor_credentials.py",
        "credential_manager.py",
        "enqueue_external_action.py",
        "execute_external_action.py",
        "executor_preflight.py",
        "executor_readiness.py",
        "install_executor_service.py",
    }
    assert denied.isdisjoint({path.name for path in scripts.iterdir()})
    parent = (SKILLS / "linkedin-campaign-orchestrator" / "SKILL.md").read_text()
    assert "Use the fixed startup route" in parent
    assert "without presenting a mode selection" in parent
    assert "scripts/service_status.py STATE_DIR" in parent


def test_public_package_contains_no_fixed_owner_identity() -> None:
    public_runtime = "\n".join(
        path.read_text(encoding="utf-8")
        for path in SKILLS.rglob("*")
        if path.is_file() and path.suffix in {".md", ".json", ".py"}
    )
    assert "sunny-chandel-6a05bb401" not in public_runtime
    assert "sunny-linkedin-10k-10k" not in public_runtime


def test_required_public_launch_surfaces_exist() -> None:
    required = [
        ROOT / "LICENSE",
        ROOT / "CONTRIBUTING.md",
        ROOT / "SUPPORT.md",
        ROOT / "CHANGELOG.md",
        ROOT / "docs" / "QUICKSTART.md",
        ROOT / "launch" / "FIVE_DAY_LAUNCH.md",
        ROOT / "launch" / "KEYWORD_MAP.md",
        ROOT / "launch" / "PRESS_RELEASE.md",
        ROOT / "launch" / "MEDIA_PITCH.md",
        ROOT / "launch" / "LINKEDIN_SEQUENCE.md",
        ROOT / "website" / "public" / "og-card.png",
        ROOT / "website" / "public" / "llms.txt",
        ROOT / "website" / "public" / "feed.xml",
        ROOT / "website" / "public" / "manifest.webmanifest",
        ROOT / "website" / "public" / "5aa097eef2230401862aaa8415746f73.txt",
        ROOT / "website" / "app" / "sitemap.ts",
        ROOT / "website" / "app" / "robots.ts",
    ]
    assert all(path.is_file() for path in required)
