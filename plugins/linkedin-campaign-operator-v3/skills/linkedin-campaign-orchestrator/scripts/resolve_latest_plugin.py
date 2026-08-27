#!/usr/bin/env python3
"""Resolve the newest installed plugin instructions for a running session."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PLUGIN_ID = "linkedin-campaign-operator-v3@sunny-linkedin-tools"
PLUGIN_NAME = "linkedin-campaign-operator-v3"


def version_key(value: str) -> tuple[int, int, int, int, int, str]:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:-rc\.(\d+))?(.*)", value)
    if not match:
        return (-1, -1, -1, -1, -1, value)
    rc_number = match.group(4)
    return (
        int(match.group(1)),
        int(match.group(2)),
        int(match.group(3)),
        1 if rc_number is None else 0,
        int(rc_number or 0),
        match.group(5),
    )


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def update_runtime_state(
    state_dir: Path,
    *,
    session_version: str,
    installed_version: str,
    install_path: Path,
    update_available: bool,
    activate: bool,
) -> dict[str, Any]:
    state_path = state_dir.expanduser().resolve() / "campaign-state.json"
    state = load_object(state_path)
    runtime = state.setdefault("runtime_instructions", {})
    if not isinstance(runtime, dict):
        raise ValueError("campaign-state.json runtime_instructions must be an object")
    now = datetime.now(timezone.utc).isoformat()
    # Once direct loading succeeds, the running session is operating with the
    # installed instructions. Normalize every current-version field so stale
    # bootstrap versions cannot be mistaken for the active runtime version.
    runtime["session_version"] = installed_version if activate else session_version
    runtime["detected_version"] = installed_version
    runtime["install_path"] = str(install_path)
    runtime["last_checked_at"] = now
    if activate:
        runtime["active_version"] = installed_version
        runtime["refresh_mode"] = "direct-loaded"
        runtime["activated_at"] = now
    elif update_available:
        runtime["refresh_mode"] = "pending-direct-load"
    state["updated_at"] = now
    atomic_write_json(state_path, state)
    return runtime


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-version", required=True)
    parser.add_argument(
        "--installed-plugins",
        type=Path,
        default=Path.home() / ".claude" / "plugins" / "installed_plugins.json",
    )
    parser.add_argument(
        "--state-dir",
        type=Path,
        help="Optional campaign directory whose runtime refresh record should be updated atomically.",
    )
    parser.add_argument(
        "--activate",
        action="store_true",
        help="Record the resolved version as active after all returned skill files were read.",
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
        effective_session_version = installed_version if args.activate else args.session_version
        effective_update_available = False if args.activate else update_available
        runtime_state = None
        if args.state_dir:
            runtime_state = update_runtime_state(
                args.state_dir,
                session_version=effective_session_version,
                installed_version=installed_version,
                install_path=install_path,
                update_available=effective_update_available,
                activate=args.activate,
            )
        print(
            json.dumps(
                {
                    "valid": True,
                    "session_version": effective_session_version,
                    "installed_version": installed_version,
                    "update_available": effective_update_available,
                    "install_path": str(install_path),
                    "orchestrator_skill": str(orchestrator),
                    "skill_files": skill_files,
                    "reload_command": "/reload-plugins",
                    "reload_command_is_optional": True,
                    "desktop_refresh_mode": "direct-load",
                    "direct_load_supported": True,
                    "runtime_state": runtime_state,
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
