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
        assert metadata["metadata"]["version"] == "6.0.0-rc.12"
        if metadata["name"] != "linkedin-campaign-orchestrator":
            assert f"`{metadata['name']}`" in parent_text


def test_claude_and_codex_manifests_are_aligned() -> None:
    claude = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())
    codex = json.loads((PLUGIN / ".codex-plugin" / "plugin.json").read_text())
    assert claude["name"] == codex["name"] == PLUGIN.name
    assert claude["version"] == codex["version"] == "6.0.0-rc.12"
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
    assert "Maintain one campaign continuation schedule" in text
    assert "update it rather than creating duplicates" in text


def test_orchestrator_uses_deterministic_plugin_path_resolution() -> None:
    text = (SKILLS / "linkedin-campaign-orchestrator" / "SKILL.md").read_text()
    assert "Resolve the newest installed plugin" in text
    assert "scripts/resolve_latest_plugin.py" in text
    assert "Load the newest parent skill and each child skill needed" in text


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
