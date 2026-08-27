#!/usr/bin/env python3
"""Persist scoped runtime repair state and deterministic recovery requests."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


CAPABILITIES = {"chrome", "claude-design", "file-upload", "computer-use", "codex"}


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain an object")
    return value


def atomic_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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


def append_event(path: Path, value: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state_dir", type=Path)
    parser.add_argument("--capability", choices=sorted(CAPABILITIES))
    parser.add_argument("--failure-evidence", type=Path)
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--doctor", action="store_true")
    parser.add_argument("--invoke-codex", action="store_true")
    parser.add_argument("--result", type=Path)
    parser.add_argument("--now")
    args = parser.parse_args()
    state_dir = args.state_dir.expanduser().resolve()
    now = datetime.fromisoformat(args.now) if args.now else datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    try:
        path = state_dir / "repair-state.json"
        state = load_object(path) if path.is_file() else {
            "schema_version": "2.0",
            "status": "healthy",
            "active_repair": None,
            "history": [],
        }
        if args.result:
            result = load_object(args.result)
            active = state.get("active_repair") or {}
            active["result"] = result
            active["completed_at"] = now.isoformat()
            active["verification_required"] = True
            state["status"] = "verification-pending"
            state["active_repair"] = active
            event_type = "repair-result-recorded"
        elif args.capability:
            evidence = load_object(args.failure_evidence) if args.failure_evidence else {}
            checkpoint = load_object(args.checkpoint) if args.checkpoint else {}
            repair_id = f"repair-{args.capability}-{now.strftime('%Y%m%dT%H%M%SZ')}"
            doctor_result: dict[str, Any] | None = None
            if args.doctor:
                try:
                    completed = subprocess.run(
                        ["codex", "doctor", "--json"],
                        check=False,
                        capture_output=True,
                        text=True,
                        timeout=120,
                    )
                    doctor_result = {
                        "exit_code": completed.returncode,
                        "stdout": completed.stdout[-12000:],
                        "stderr": completed.stderr[-4000:],
                    }
                except (OSError, subprocess.TimeoutExpired) as exc:
                    doctor_result = {"error": str(exc)}
            request = {
                "repair_id": repair_id,
                "capability": args.capability,
                "detected_at": now.isoformat(),
                "failure_evidence": evidence,
                "checkpoint": checkpoint,
                "recovery_order": [
                    "current-agent-computer-use",
                    "reopen-refresh-or-rebind",
                    "rerun-specific-preflight",
                    "codex-doctor-json",
                    "scoped-ephemeral-codex-repair",
                    "verify-and-resume-lease",
                ],
                "codex_scope": {
                    "allowed": [
                        "application-session-recovery",
                        "deterministic-campaign-state-repair",
                        "reinstall-currently-approved-plugin-version",
                    ],
                    "forbidden": [
                        "modify-skill-instructions",
                        "modify-source-code",
                        "modify-git-history",
                        "publish-linkedin-content",
                    ],
                },
                "doctor_result": doctor_result,
                "retry_trigger": (now + timedelta(minutes=15)).isoformat(),
                "continue_unaffected_work": True,
            }
            if args.invoke_codex:
                schema_path = Path(__file__).resolve().parent.parent / "assets" / "repair-result.schema.json"
                with tempfile.NamedTemporaryFile(prefix="codex-repair-result-", suffix=".json", delete=False) as handle:
                    result_path = Path(handle.name)
                prompt = (
                    "Perform only scoped runtime recovery. Do not modify skill instructions, source code, "
                    "Git history, or publish LinkedIn content. You may recover the application/session, "
                    "repair deterministic state under the campaign directory, or reinstall the already-approved "
                    f"plugin version. Capability: {args.capability}. Campaign: {state_dir}. "
                    f"Failure evidence: {json.dumps(evidence, ensure_ascii=False)}. "
                    f"Resume checkpoint: {json.dumps(checkpoint, ensure_ascii=False)}. "
                    "Use computer use when available, verify the result, and return the required JSON."
                )
                command = [
                    "codex", "exec", "--ephemeral", "--json", "--sandbox", "workspace-write",
                    "--approve-for-me", "--skip-git-repo-check", "-C", str(state_dir),
                    "-c", "features.computer_use=true", "--output-schema", str(schema_path),
                    "--output-last-message", str(result_path), prompt,
                ]
                try:
                    completed = subprocess.run(
                        command, check=False, capture_output=True, text=True, timeout=900
                    )
                    codex_result = None
                    if result_path.is_file() and result_path.stat().st_size:
                        try:
                            codex_result = load_object(result_path)
                        except (OSError, json.JSONDecodeError, ValueError):
                            codex_result = None
                    request["codex_handoff"] = {
                        "exit_code": completed.returncode,
                        "result": codex_result,
                        "stdout_tail": completed.stdout[-12000:],
                        "stderr_tail": completed.stderr[-4000:],
                        "ephemeral": True,
                        "computer_use_requested": True,
                    }
                except (OSError, subprocess.TimeoutExpired) as exc:
                    request["codex_handoff"] = {"error": str(exc), "retry_required": True}
                finally:
                    try:
                        result_path.unlink()
                    except FileNotFoundError:
                        pass
            state["status"] = "repair-pending"
            state["active_repair"] = request
            event_type = "repair-requested"
        else:
            event_type = "repair-state-read"
        state["schema_version"] = "2.0"
        state["updated_at"] = now.isoformat()
        atomic_write(path, state)
        append_event(state_dir / "repair-events.jsonl", {
            "schema_version": "2.0",
            "event_type": event_type,
            "recorded_at": now.isoformat(),
            "active_repair": state.get("active_repair"),
        })
        print(json.dumps({"valid": True, "repair_state": state}, indent=2, ensure_ascii=False))
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
