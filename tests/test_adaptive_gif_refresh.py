#!/usr/bin/env python3
"""Regression tests for engagement ranking, GIF intelligence, branding, and refresh."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "linkedin-campaign-operator-v3"
BRAND_SCRIPTS = PLUGIN / "skills" / "linkedin-brand-system" / "scripts"
GIF_SCRIPTS = PLUGIN / "skills" / "linkedin-gif-creative-intelligence" / "scripts"
ENGAGEMENT_SCRIPTS = PLUGIN / "skills" / "linkedin-engagement-planning" / "scripts"
ORCHESTRATOR_SCRIPTS = PLUGIN / "skills" / "linkedin-campaign-orchestrator" / "scripts"
PLUGIN_ID = "linkedin-campaign-operator-v3@sunny-linkedin-tools"


def run_json(arguments: list[str]) -> dict:
    completed = subprocess.run(arguments, check=True, capture_output=True, text=True)
    return json.loads(completed.stdout)


class AdaptiveGifRefreshTests(unittest.TestCase):
    def test_watermark_and_gif_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            watermark = root / "watermark.png"
            image = Image.new("RGBA", (1600, 320), (0, 0, 0, 0))
            ImageDraw.Draw(image).rectangle((100, 100, 1500, 220), fill=(255, 255, 255, 220))
            image.save(watermark)
            checked = run_json(
                [
                    "python3",
                    str(BRAND_SCRIPTS / "validate_watermark.py"),
                    str(watermark),
                    "--expected-width",
                    "1600",
                    "--expected-height",
                    "320",
                ]
            )
            self.assertTrue(checked["valid"])
            self.assertIsNotNone(checked["sha256"])

            gif = root / "reference.gif"
            frames = [
                Image.new("RGB", (320, 180), color=color)
                for color in ((255, 0, 0), (0, 255, 0), (0, 0, 255))
            ]
            frames[0].save(gif, save_all=True, append_images=frames[1:], duration=[80, 100, 120], loop=0)
            inspected = run_json(["python3", str(GIF_SCRIPTS / "inspect_gif.py"), str(gif)])
            self.assertTrue(inspected["valid"])
            self.assertEqual(inspected["frame_count"], 3)
            self.assertEqual(inspected["total_duration_ms"], 300)

    def test_action_and_reference_ranking(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            action_input = root / "actions.json"
            action_input.write_text(
                json.dumps(
                    {
                        "campaign_id": "test",
                        "candidates": [
                            {
                                "candidate_id": "qualified-comment",
                                "action_type": "comment",
                                "qualified": True,
                                "cooldown_passed": True,
                                "action_available": True,
                                "capacity_available": True,
                                "qualified_growth": 0.9,
                                "audience_spillover": 0.9,
                                "conversation_probability": 0.8,
                                "target_relevance": 1,
                                "freshness_timing": 0.9,
                                "historical_performance": 0.8,
                            },
                            {
                                "candidate_id": "below-threshold",
                                "qualified": True,
                                "cooldown_passed": True,
                                "action_available": True,
                                "capacity_available": True,
                                "qualified_growth": 0.1,
                                "audience_spillover": 0.1,
                                "conversation_probability": 0.1,
                                "target_relevance": 0.1,
                                "freshness_timing": 0.1,
                                "historical_performance": 0.1,
                            },
                            {
                                "candidate_id": "cooldown-failed",
                                "qualified": True,
                                "cooldown_passed": False,
                                "action_available": True,
                                "capacity_available": True,
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            action_plan = run_json(["python3", str(ENGAGEMENT_SCRIPTS / "rank_actions.py"), str(action_input)])
            self.assertEqual([item["candidate_id"] for item in action_plan["selected"]], ["qualified-comment"])
            reasons = {item["candidate_id"]: item["reason"] for item in action_plan["rejected"]}
            self.assertEqual(reasons["below-threshold"], "below-threshold")
            self.assertEqual(reasons["cooldown-failed"], "hard-gate")

            reference_input = root / "references.json"
            reference_input.write_text(
                json.dumps(
                    {
                        "campaign_id": "test",
                        "references": [
                            {
                                "reference_id": "best",
                                "information_quality": 1,
                                "normalized_engagement": 0.9,
                                "visual_execution": 0.9,
                                "recency": 1,
                                "audience_fit": 1,
                            },
                            {
                                "reference_id": "second",
                                "information_quality": 0.6,
                                "normalized_engagement": 0.6,
                                "visual_execution": 0.6,
                                "recency": 0.6,
                                "audience_fit": 0.6,
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            ranked = run_json(["python3", str(GIF_SCRIPTS / "score_gif_references.py"), str(reference_input)])
            self.assertEqual(ranked["selected_reference_id"], "best")
            self.assertGreater(ranked["references"][0]["reference_score"], 85)

    def test_dominant_pattern_permanently_deletes_old_capture(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            captures = root / "captures"
            captures.mkdir()
            old_capture = captures / "old.gif"
            old_capture.write_bytes(b"old")
            library = root / "library.json"
            library.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "patterns": [
                            {
                                "pattern_id": "old",
                                "reference_score": 70,
                                "capture_paths": ["old.gif"],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            candidate = root / "candidate.json"
            candidate.write_text(
                json.dumps(
                    {
                        "pattern_id": "new",
                        "reference_score": 90,
                        "contradicts_pattern_id": "old",
                        "capture_paths": [],
                    }
                ),
                encoding="utf-8",
            )
            result = run_json(
                [
                    "python3",
                    str(GIF_SCRIPTS / "promote_gif_pattern.py"),
                    str(library),
                    str(candidate),
                    "--capture-root",
                    str(captures),
                ]
            )
            self.assertEqual(result["deleted_pattern_id"], "old")
            self.assertFalse(old_capture.exists())
            patterns = json.loads(library.read_text(encoding="utf-8"))["patterns"]
            self.assertEqual([item["pattern_id"] for item in patterns], ["new"])

    def test_resolver_finds_newer_installed_instructions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            install = root / "cache" / "0.5.0"
            (install / ".claude-plugin").mkdir(parents=True)
            (install / "skills" / "linkedin-campaign-orchestrator").mkdir(parents=True)
            (install / ".claude-plugin" / "plugin.json").write_text(
                json.dumps({"name": "linkedin-campaign-operator-v3", "version": "0.5.0"}),
                encoding="utf-8",
            )
            (install / "skills" / "linkedin-campaign-orchestrator" / "SKILL.md").write_text(
                "---\nname: linkedin-campaign-orchestrator\ndescription: test\n---\n",
                encoding="utf-8",
            )
            registry = root / "installed_plugins.json"
            registry.write_text(
                json.dumps(
                    {
                        "plugins": {
                            PLUGIN_ID: [
                                {"scope": "user", "installPath": str(install), "version": "0.5.0"}
                            ]
                        }
                    }
                ),
                encoding="utf-8",
            )
            state_dir = root / "campaign-data"
            state_dir.mkdir()
            state_path = state_dir / "campaign-state.json"
            state_path.write_text(
                json.dumps(
                    {
                        "campaign_id": "test",
                        "runtime_instructions": {
                            "session_version": "0.3.3",
                            "active_version": "0.3.3",
                            "install_path": None,
                            "refresh_mode": "session-loaded",
                        },
                    }
                ),
                encoding="utf-8",
            )
            base_arguments = [
                "python3",
                str(ORCHESTRATOR_SCRIPTS / "resolve_latest_plugin.py"),
                "--session-version",
                "0.3.3",
                "--installed-plugins",
                str(registry),
                "--state-dir",
                str(state_dir),
            ]
            resolved = run_json(
                [
                    *base_arguments,
                ]
            )
            self.assertTrue(resolved["update_available"])
            self.assertEqual(resolved["installed_version"], "0.5.0")
            self.assertEqual(resolved["reload_command"], "/reload-plugins")
            self.assertEqual(resolved["desktop_refresh_mode"], "direct-load")
            pending = json.loads(state_path.read_text(encoding="utf-8"))["runtime_instructions"]
            self.assertEqual(pending["active_version"], "0.3.3")
            self.assertEqual(pending["detected_version"], "0.5.0")
            self.assertEqual(pending["refresh_mode"], "pending-direct-load")

            activated = run_json([*base_arguments, "--activate"])
            self.assertEqual(activated["runtime_state"]["active_version"], "0.5.0")
            active = json.loads(state_path.read_text(encoding="utf-8"))["runtime_instructions"]
            self.assertEqual(active["active_version"], "0.5.0")
            self.assertEqual(active["install_path"], str(install.resolve()))
            self.assertEqual(active["refresh_mode"], "direct-loaded")


if __name__ == "__main__":
    unittest.main()
