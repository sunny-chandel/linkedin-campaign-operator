#!/usr/bin/env python3
"""Validate durable state and return the one next campaign step."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from package_version import CURRENT_VERSION


SKILL_BY_TASK_TYPE = {
    "opportunity-discovery": "linkedin-opportunity-discovery",
    "engagement-opportunity-generation": "linkedin-opportunity-discovery",
    "engagement-burst": "linkedin-engagement-execution",
    "engagement-burst-execution": "linkedin-engagement-execution",
    "soft-reciprocity": "linkedin-engagement-execution",
    "direct-inbound": "linkedin-engagement-execution",
    "comment": "linkedin-engagement-execution",
    "reply": "linkedin-engagement-execution",
    "direct-message": "linkedin-engagement-execution",
    "regional-allocation": "linkedin-regional-intelligence",
    "two-package-production": "linkedin-content-production",
    "six-package-replenishment": "linkedin-content-production",
    "performance-recovery-content": "linkedin-content-production",
    "publication-opportunity": "linkedin-publishing-operations",
    "publication-execution": "linkedin-publishing-operations",
    "publication-queue-building": "linkedin-publishing-operations",
    "publishing-debt-recovery": "linkedin-publishing-operations",
    "scheduled-analytics-snapshot": "linkedin-analytics-learning",
    "opportunity-health-evaluation": "linkedin-analytics-learning",
    "performance-recovery-analytics": "linkedin-analytics-learning",
    "analytics-and-investigation": "linkedin-analytics-learning",
    "runtime-repair": "linkedin-runtime-repair",
}


def run_json(script_dir: Path, script: str, arguments: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, str(script_dir / script), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )
    raw = completed.stdout.strip() or completed.stderr.strip()
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{script} did not return JSON: {raw}") from exc
    if completed.returncode:
        raise ValueError(f"{script} failed: {value}")
    if not isinstance(value, dict):
        raise ValueError(f"{script} must return a JSON object")
    return value


def runtime_version(state_dir: Path) -> str | None:
    path = state_dir / "campaign-state.json"
    if not path.is_file():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        return None
    instructions = value.get("runtime_instructions", {})
    if not isinstance(instructions, dict):
        return None
    version = instructions.get("active_version")
    return str(version) if version else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state_dir", type=Path)
    parser.add_argument("--session-start", action="store_true")
    parser.add_argument("--session-id", default="claude-code-campaign-session")
    parser.add_argument("--now", help="ISO timestamp used in deterministic tests")
    args = parser.parse_args()

    state_dir = args.state_dir.expanduser().resolve()
    script_dir = Path(__file__).resolve().parent
    common = [str(state_dir)]
    timed = [*common, "--now", args.now] if args.now else common
    report: dict[str, Any] = {
        "valid": True,
        "plugin_version": CURRENT_VERSION,
        "state_dir": str(state_dir),
    }
    try:
        if args.session_start or runtime_version(state_dir) != CURRENT_VERSION:
            report["migration"] = run_json(script_dir, "migrate_campaign.py", timed)
        consent_path = state_dir / "consent-record.json"
        consent = (
            json.loads(consent_path.read_text(encoding="utf-8"))
            if consent_path.is_file()
            else {}
        )
        consent_active = isinstance(consent, dict) and consent.get("status") == "active"
        validation_arguments = common if consent_active else [*common, "--allow-draft"]
        report["validation"] = run_json(
            script_dir, "validate_campaign.py", validation_arguments
        )
        if not consent_active:
            report["next_action"] = {
                "kind": "record-current-owner-start-consent",
                "command": "runtime_control.py STATE_DIR consent-grant",
                "then": "rerun campaign_cycle.py with --session-start",
            }
            print(json.dumps(report, indent=2, ensure_ascii=False))
            return 0
        if args.session_start:
            resume_arguments = [*common, "--session-id", args.session_id]
            if args.now:
                resume_arguments.extend(["--now", args.now])
            report["resume"] = run_json(script_dir, "resume_campaign.py", resume_arguments)
        audit_arguments = [*common, "--write"]
        if args.now:
            audit_arguments.extend(["--now", args.now])
        report["audit"] = run_json(script_dir, "audit_pipeline.py", audit_arguments)
        dispatch_arguments = [*common, "--record"]
        if args.now:
            dispatch_arguments.extend(["--now", args.now])
        decision = run_json(script_dir, "dispatch_next_work.py", dispatch_arguments)
        report["dispatch"] = decision
        task = decision.get("task")
        if decision.get("decision") == "execute" and isinstance(task, dict):
            task_type = str(task.get("task_type") or "")
            report["next_action"] = {
                "kind": "execute-child-task",
                "task_id": task.get("task_id"),
                "task_type": task_type,
                "skill": SKILL_BY_TASK_TYPE.get(task_type, "linkedin-campaign-orchestrator"),
                "after_save": "run campaign_cycle.py again without --session-start",
            }
        elif decision.get("decision") == "wait":
            report["next_action"] = {
                "kind": "wait-for-recorded-trigger",
                "next_wake_at": decision.get("predicted_next_opportunity"),
                "wake_trigger": decision.get("wake_trigger"),
            }
        elif decision.get("decision") == "consent-required":
            report["next_action"] = {
                "kind": "record-current-owner-start-consent",
                "command": "runtime_control.py STATE_DIR consent-grant",
            }
        else:
            report["next_action"] = {"kind": str(decision.get("decision") or "inspect")}
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(
            json.dumps(
                {
                    "valid": False,
                    "plugin_version": CURRENT_VERSION,
                    "state_dir": str(state_dir),
                    "error": str(exc),
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
