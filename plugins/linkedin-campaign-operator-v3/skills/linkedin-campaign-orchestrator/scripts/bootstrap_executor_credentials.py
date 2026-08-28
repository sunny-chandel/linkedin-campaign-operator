#!/usr/bin/env python3
"""Copy one-time LinkedIn OAuth material from environment variables into macOS Keychain."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Mapping


REQUIRED = ("actor_urn", "client_id", "client_secret", "refresh_token")


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def env_name(source: Mapping[str, Any], logical_name: str) -> str:
    default = "LINKEDIN_" + logical_name.upper()
    value = source.get(f"{logical_name}_env")
    return value if isinstance(value, str) and value else default


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state_dir", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        state_dir = args.state_dir.expanduser().resolve()
        executor = load_object(state_dir / "external-executor.json")
        source = executor.get("credential_source", {})
        keychain = source.get("keychain", {}) if isinstance(source, Mapping) else {}
        service = keychain.get("service") if isinstance(keychain, Mapping) else None
        accounts = keychain.get("accounts", {}) if isinstance(keychain, Mapping) else {}
        if not isinstance(service, str) or not service or not isinstance(accounts, Mapping):
            raise ValueError("external executor does not define a macOS Keychain destination")
        values: dict[str, str] = {}
        missing: list[str] = []
        for logical_name in REQUIRED + ("access_token",):
            name = env_name(source, logical_name)
            value = os.environ.get(name)
            if value:
                values[logical_name] = value
            elif logical_name in REQUIRED:
                missing.append(name)
        if missing:
            print(json.dumps({
                "valid": False,
                "decision": "one-time-oauth-material-unavailable",
                "missing_environment_variables": missing,
                "secrets_logged": False,
            }, indent=2))
            return 2
        planned = []
        for logical_name, value in values.items():
            account = accounts.get(logical_name)
            if not isinstance(account, str) or not account:
                raise ValueError(f"missing Keychain account mapping for {logical_name}")
            planned.append({"logical_name": logical_name, "service": service, "account": account})
            if not args.dry_run:
                completed = subprocess.run(
                    [
                        "security", "add-generic-password", "-U", "-s", service,
                        "-a", account, "-w", value,
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                if completed.returncode:
                    raise ValueError(f"Keychain write failed for {logical_name}")
        print(json.dumps({
            "valid": True,
            "decision": "dry-run" if args.dry_run else "stored-in-macos-keychain",
            "stored": planned,
            "secret_values_returned": False,
        }, indent=2))
        return 0
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc), "secret_values_returned": False}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
