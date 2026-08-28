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
        assert metadata["metadata"]["version"] == "6.0.0-rc.7"
        if metadata["name"] != "linkedin-campaign-orchestrator":
            assert f"`{metadata['name']}`" in parent_text


def test_claude_and_codex_manifests_are_aligned() -> None:
    claude = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())
    codex = json.loads((PLUGIN / ".codex-plugin" / "plugin.json").read_text())
    assert claude["name"] == codex["name"] == PLUGIN.name
    assert claude["version"] == codex["version"] == "6.0.0-rc.7"
    assert claude["license"] == codex["license"] == "MIT"
    assert claude["homepage"] == codex["homepage"] == PUBLIC_SITE
    assert codex["skills"] == "./skills/"


def test_orchestrator_selects_exact_pinned_browser_without_question() -> None:
    text = (SKILLS / "linkedin-campaign-orchestrator" / "SKILL.md").read_text()
    assert "Resolve the pinned Chrome device" in text
    assert "verify the stored profile identity" in text
    assert "routes to `linkedin-runtime-repair`" in text
    assert "retry automatically" in text


def test_runtime_classification_is_agent_neutral() -> None:
    text = (SKILLS / "linkedin-campaign-orchestrator" / "SKILL.md").read_text()
    assert "Claude, Codex, and compatible agents" in text
    assert "canonical" in text


def test_continuation_never_becomes_an_owner_choice() -> None:
    text = (SKILLS / "linkedin-campaign-orchestrator" / "SKILL.md").read_text()
    assert "Renew it before any host duration limit" in text
    assert "The dispatcher selects this continuation mechanism" in text


def test_orchestrator_uses_deterministic_plugin_path_resolution() -> None:
    text = (SKILLS / "linkedin-campaign-orchestrator" / "SKILL.md").read_text()
    assert "Resolve the newest installed plugin at every wake" in text
    assert "scripts/resolve_latest_plugin.py" in text
    assert "load the returned parent and every relevant child `SKILL.md` completely" in text


def test_v6_operational_contracts_and_internal_routes_are_explicit() -> None:
    text = (SKILLS / "linkedin-campaign-orchestrator" / "SKILL.md").read_text()
    assert "at least 160 qualified counted actions" in text
    assert "never exceed 200" in text
    assert "at least six and at most eight verified publications" in text
    assert "at least 40 currently executable records" in text
    assert "absolute 120-minute publication-spacing floor" in text
    for child in (
        "linkedin-opportunity-discovery",
        "linkedin-engagement-execution",
        "linkedin-regional-intelligence",
        "linkedin-publishing-operations",
        "linkedin-runtime-repair",
    ):
        assert f"`{child}`" in text


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
