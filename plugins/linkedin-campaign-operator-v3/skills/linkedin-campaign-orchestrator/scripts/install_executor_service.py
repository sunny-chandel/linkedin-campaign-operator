#!/usr/bin/env python3
"""Install and start one per-campaign macOS LaunchAgent for the autonomous outbox."""

from __future__ import annotations

import argparse
import json
import os
import plistlib
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from executor_readiness import readiness_report


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state_dir", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        state_dir = args.state_dir.expanduser().resolve()
        executor = load_object(state_dir / "external-executor.json")
        config = load_object(state_dir / "campaign-config.json")
        required = {
            str(value)
            for value in config.get("autonomous_execution", {}).get(
                "required_action_classes", ["publication", "comment", "reply", "reaction"]
            )
            if isinstance(value, str)
        }
        keychain_readiness = readiness_report(executor, required, environ={})
        if not keychain_readiness["unattended_ready"]:
            print(json.dumps({
                "valid": False,
                "decision": "keychain-backed-readiness-required",
                "readiness": keychain_readiness,
            }, indent=2))
            return 2
        campaign_id = str(executor.get("campaign_id") or state_dir.name)
        safe_id = re.sub(r"[^a-zA-Z0-9.-]+", "-", campaign_id).strip("-").lower()
        label = f"com.sunny.linkedin-campaign-operator.{safe_id}"
        daemon = Path(__file__).resolve().with_name("autonomous_executor_daemon.py")
        logs = state_dir / "logs"
        logs.mkdir(exist_ok=True)
        plist = {
            "Label": label,
            "ProgramArguments": [
                sys.executable,
                str(daemon),
                str(state_dir),
                "--poll-seconds",
                "15",
            ],
            "RunAtLoad": True,
            "KeepAlive": True,
            "ProcessType": "Background",
            "WorkingDirectory": str(state_dir.parent.parent),
            "StandardOutPath": str(logs / "external-executor-daemon.stdout.log"),
            "StandardErrorPath": str(logs / "external-executor-daemon.stderr.log"),
        }
        destination = Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"
        if args.dry_run:
            print(json.dumps({
                "valid": True,
                "decision": "dry-run",
                "label": label,
                "destination": str(destination),
                "plist": plist,
            }, indent=2))
            return 0
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(".plist.tmp")
        temporary.write_bytes(plistlib.dumps(plist, fmt=plistlib.FMT_XML, sort_keys=True))
        os.replace(temporary, destination)
        domain = f"gui/{os.getuid()}"
        subprocess.run(["launchctl", "bootout", domain, str(destination)], check=False, capture_output=True)
        completed = subprocess.run(
            ["launchctl", "bootstrap", domain, str(destination)],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode:
            raise ValueError("launchctl bootstrap failed")
        subprocess.run(["launchctl", "kickstart", "-k", f"{domain}/{label}"], check=False)
        print(json.dumps({
            "valid": True,
            "decision": "installed-and-started",
            "label": label,
            "plist": str(destination),
        }, indent=2))
        return 0
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
