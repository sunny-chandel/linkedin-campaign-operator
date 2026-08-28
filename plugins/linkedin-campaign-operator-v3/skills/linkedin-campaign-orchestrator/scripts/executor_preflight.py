#!/usr/bin/env python3
"""Verify official LinkedIn executor identity, token scopes, and refresh readiness."""

from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from executor_readiness import READ_SCOPES, WRITE_SCOPES, normalize_action_class
from credential_manager import credential_availability, resolve_credentials


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def atomic_write(path: Path, value: Mapping[str, Any]) -> None:
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(dict(value), handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def introspect_token(
    token: str,
    client_id: str,
    client_secret: str,
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    request = Request(
        "https://www.linkedin.com/oauth/v2/introspectToken",
        data=urlencode(
            {"client_id": client_id, "client_secret": client_secret, "token": token}
        ).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with opener(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("LinkedIn token introspection returned a non-object")
    return payload


def fetch_member_identity(
    token: str,
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    errors: list[str] = []
    for url in ("https://api.linkedin.com/v2/userinfo", "https://api.linkedin.com/v2/me"):
        try:
            request = Request(url, headers={"Authorization": f"Bearer {token}"})
            with opener(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("identity response was not an object")
            member_id = payload.get("sub") or payload.get("id")
            if not isinstance(member_id, str) or not member_id:
                raise ValueError("identity response did not include sub or id")
            name = payload.get("name")
            if not isinstance(name, str):
                parts = [payload.get("localizedFirstName"), payload.get("localizedLastName")]
                name = " ".join(str(part) for part in parts if isinstance(part, str)).strip()
            return {
                "actor_urn": f"urn:li:person:{member_id}",
                "display_name": name or None,
                "source": url,
            }
        except Exception as exc:  # Try the documented alternate identity endpoint.
            errors.append(f"{url}:{type(exc).__name__}")
    raise ValueError("LinkedIn identity verification failed: " + ",".join(errors))


def parse_scopes(value: object) -> set[str]:
    if isinstance(value, list):
        return {str(item) for item in value if isinstance(item, str) and item}
    if not isinstance(value, str):
        return set()
    return {item for item in re.split(r"[\s,]+", value.strip()) if item}


def supported_classes(scopes: set[str]) -> list[str]:
    if "w_member_social_feed" in scopes:
        return ["comment", "publication", "reaction", "reply"]
    if "w_member_social" in scopes:
        return ["publication"]
    return []


def evaluate_preflight(
    executor: dict[str, Any],
    config: Mapping[str, Any],
    consent: Mapping[str, Any],
    *,
    environ: Mapping[str, str] | None = None,
    introspector: Callable[[str, str, str], Mapping[str, Any]] = introspect_token,
    identity_fetcher: Callable[[str], Mapping[str, Any]] = fetch_member_identity,
    now: datetime | None = None,
) -> dict[str, Any]:
    checked_at = (now or datetime.now(timezone.utc)).isoformat()
    availability = credential_availability(executor, environ)
    missing: list[str] = []
    if not availability["access_token_resolvable"]:
        missing.append("access-token-or-programmatic-refresh")
    if not availability["programmatic_refresh_ready"]:
        missing.append("programmatic-token-refresh")
    source = executor.get("credential_source", {})
    if not isinstance(source, Mapping):
        source = {}
    credentials = None
    introspection: Mapping[str, Any] = {}
    identity: Mapping[str, Any] = {}
    if not missing:
        credentials = resolve_credentials(executor, environ)
        if not credentials.client_id or not credentials.client_secret:
            missing.append("token-introspection-client-credentials")
        else:
            introspection = introspector(
                credentials.access_token,
                credentials.client_id,
                credentials.client_secret,
            )
            if introspection.get("active") is not True or introspection.get("status") != "active":
                missing.append("active-linkedin-access-token")
            identity = identity_fetcher(credentials.access_token)
    scopes = parse_scopes(introspection.get("scope"))
    classes = supported_classes(scopes)
    required_values = config.get("autonomous_execution", {}).get(
        "required_action_classes", ["publication", "comment", "reply", "reaction"]
    )
    required = {
        action_class
        for value in required_values
        if (action_class := normalize_action_class(value))
    }
    uncovered = sorted(required - set(classes))
    if not (scopes & WRITE_SCOPES):
        missing.append("verified-linkedin-write-scope")
    if not (scopes & READ_SCOPES):
        missing.append("verified-linkedin-read-scope")
    missing.extend(f"uncovered-action-class:{value}" for value in uncovered)
    verified_actor = identity.get("actor_urn")
    configured_actor = credentials.actor_urn if credentials else None
    identity_verified = bool(
        isinstance(verified_actor, str)
        and verified_actor.startswith("urn:li:person:")
        and configured_actor == verified_actor
    )
    if not identity_verified:
        missing.append("verified-actor-identity")
    expected_name = consent.get("owner", {}).get("display_name")
    observed_name = identity.get("display_name")
    if (
        isinstance(expected_name, str)
        and expected_name.strip()
        and isinstance(observed_name, str)
        and observed_name.strip()
        and expected_name.strip().casefold() != observed_name.strip().casefold()
    ):
        missing.append("verified-owner-name-mismatch")
    missing = list(dict.fromkeys(missing))
    passed = not missing
    verification = executor.setdefault("verification", {})
    if not isinstance(verification, dict):
        verification = {}
        executor["verification"] = verification
    verification.update(
        {
            "status": "passed" if passed else "failed",
            "identity_verified": identity_verified,
            "verified_at": checked_at,
            "verified_actor_urn": verified_actor if identity_verified else configured_actor,
            "verified_display_name": observed_name,
            "write_scope_verified": bool(scopes & WRITE_SCOPES),
            "read_scope_verified": bool(scopes & READ_SCOPES),
            "token_active": introspection.get("active") is True,
            "token_expires_at_epoch": introspection.get("expires_at"),
            "auth_type": introspection.get("auth_type"),
            "credential_origins": availability.get("origins", {}),
            "missing_capabilities": missing,
        }
    )
    executor["declared_scopes"] = sorted(scopes)
    executor["supported_action_classes"] = classes
    executor["status"] = "active" if passed else "blocked"
    executor["last_preflight_at"] = checked_at
    return {
        "valid": passed,
        "unattended_ready": passed,
        "status": executor["status"],
        "supported_action_classes": classes,
        "declared_scopes": sorted(scopes),
        "missing_capabilities": missing,
        "credential_availability": availability,
        "secrets_persisted_in_campaign_state": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state_dir", type=Path)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()
    state_dir = args.state_dir.expanduser().resolve()
    try:
        executor_path = state_dir / "external-executor.json"
        executor = load_object(executor_path)
        config = load_object(state_dir / "campaign-config.json")
        consent = load_object(state_dir / "consent-record.json")
        report = evaluate_preflight(executor, config, consent)
        if not args.no_write:
            atomic_write(executor_path, executor)
        print(json.dumps({"report": report, "executor": executor}, indent=2, ensure_ascii=False))
        return 0 if report["valid"] else 2
    except Exception as exc:
        print(json.dumps({"valid": False, "error": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
