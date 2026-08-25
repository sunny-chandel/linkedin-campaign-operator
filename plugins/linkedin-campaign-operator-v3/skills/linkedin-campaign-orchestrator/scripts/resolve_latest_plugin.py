#!/usr/bin/env python3
"""Resolve the newest installed plugin instructions for a running session."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


PLUGIN_ID = "linkedin-campaign-operator-v3@sunny-linkedin-tools"
PLUGIN_NAME = "linkedin-campaign-operator-v3"


def version_key(value: str) -> tuple[int, int, int, str]:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(.*)", value)
    if not match:
        return (-1, -1, -1, value)
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)), match.group(4))


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-version", required=True)
    parser.add_argument(
        "--installed-plugins",
        type=Path,
        default=Path.home() / ".claude" / "plugins" / "installed_plugins.json",
    )
    args = parser.parse_args()

    try:
        installed = load_object(args.installed_plugins)
        entries = installed.get("plugins", {}).get(PLUGIN_ID, [])
        if not isinstance(entries, list) or not entries:
            raise ValueError(f"installed plugin not found: {PLUGIN_ID}")
        entry = max(entries, key=lambda item: version_key(str(item.get("version", ""))))
        install_path = Path(entry.get("installPath", "")).expanduser().resolve()
        manifest_path = install_path / ".claude-plugin" / "plugin.json"
        manifest = load_object(manifest_path)
        if manifest.get("name") != PLUGIN_NAME:
            raise ValueError("installed manifest name does not match the expected plugin")
        installed_version = str(manifest.get("version", ""))
        if installed_version != str(entry.get("version", "")):
            raise ValueError("installed registry and manifest versions do not match")
        skill_files = sorted(str(path) for path in (install_path / "skills").glob("*/SKILL.md"))
        orchestrator = install_path / "skills" / "linkedin-campaign-orchestrator" / "SKILL.md"
        if not orchestrator.is_file():
            raise ValueError("latest orchestrator SKILL.md is missing")
        update_available = version_key(installed_version) > version_key(args.session_version)
        print(
            json.dumps(
                {
                    "valid": True,
                    "session_version": args.session_version,
                    "installed_version": installed_version,
                    "update_available": update_available,
                    "install_path": str(install_path),
                    "orchestrator_skill": str(orchestrator),
                    "skill_files": skill_files,
                    "reload_command": "/reload-plugins",
                    "direct_load_supported": True,
                },
                indent=2,
            )
        )
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
