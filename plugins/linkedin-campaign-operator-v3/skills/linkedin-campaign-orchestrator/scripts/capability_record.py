#!/usr/bin/env python3
"""Resolve LinkedIn executor credentials without persisting secrets in campaign JSON."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any, Callable, Mapping
from urllib.parse import urlencode
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class Credentials:
    access_token: str
    actor_urn: str
    source: str
    client_id: str | None = None
    client_secret: str | None = None
    refreshed: bool = False
    expires_in: int | None = None
    refresh_token_expires_in: int | None = None


def _name(source: Mapping[str, Any], field: str, default: str) -> str:
    value = source.get(field)
    return value if isinstance(value, str) and value else default


def _keychain_value(service: str, account: str) -> str | None:
    security_cli = shutil.which("security")
    if not security_cli:
        return None
    try:
        completed = subprocess.run(
            [security_cli, "find-generic-password", "-s", service, "-a", account, "-w"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if completed.returncode:
        return None
    return completed.stdout.strip() or None


def _keychain_accounts(source: Mapping[str, Any]) -> tuple[str | None, Mapping[str, Any]]:
    keychain = source.get("keychain", {})
    if not isinstance(keychain, Mapping):
        return None, {}
    service = keychain.get("service")
    accounts = keychain.get("accounts", {})
    return (
        service if isinstance(service, str) and service else None,
        accounts if isinstance(accounts, Mapping) else {},
    )


def secret_value(
    source: Mapping[str, Any],
    logical_name: str,
    environ: Mapping[str, str] | None = None,
) -> tuple[str | None, str | None]:
    environment = os.environ if environ is None else environ
    defaults = {
        "access_token": "LINKEDIN_ACCESS_TOKEN",
        "actor_urn": "LINKEDIN_ACTOR_URN",
        "client_id": "LINKEDIN_CLIENT_ID",
        "client_secret": "LINKEDIN_CLIENT_SECRET",
        "refresh_token": "LINKEDIN_REFRESH_TOKEN",
    }
    env_name = _name(source, f"{logical_name}_env", defaults[logical_name])
    env_value = environment.get(env_name)
    if env_value:
        return env_value, f"environment:{env_name}"
    source_type = str(source.get("type") or "environment")
    if "macos-keychain" not in source_type:
        return None, None
    service, accounts = _keychain_accounts(source)
    account = accounts.get(logical_name)
    if not service or not isinstance(account, str) or not account:
        return None, None
    value = _keychain_value(service, account)
    return (value, f"macos-keychain:{service}:{account}") if value else (None, None)


def credential_availability(
    executor: Mapping[str, Any],
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    source = executor.get("credential_source", {})
    if not isinstance(source, Mapping):
        source = {}
    found: dict[str, bool] = {}
    origins: dict[str, str] = {}
    for logical_name in (
        "access_token",
        "actor_urn",
        "client_id",
        "client_secret",
        "refresh_token",
    ):
        value, origin = secret_value(source, logical_name, environ)
        found[logical_name] = bool(value)
        if origin:
            origins[logical_name] = origin
    verified_actor = executor.get("verification", {}).get("verified_actor_urn")
    if not found["actor_urn"] and isinstance(verified_actor, str) and verified_actor:
        found["actor_urn"] = True
        origins["actor_urn"] = "external-executor.json:verified_actor_urn"
    refresh = executor.get("token_refresh", {})
    if not isinstance(refresh, Mapping):
        refresh = {}
    refresh_ready = (
        refresh.get("mode") == "programmatic"
        and found["client_id"]
        and found["client_secret"]
        and found["refresh_token"]
    )
    return {
        "available": found,
        "origins": origins,
        "access_token_resolvable": found["access_token"] or refresh_ready,
        "programmatic_refresh_ready": refresh_ready,
    }


def refresh_access_token(
    client_id: str,
    client_secret: str,
    refresh_token: str,
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    encoded = urlencode(
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
        }
    ).encode("utf-8")
    request = Request(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data=encoded,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with opener(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("access_token"), str):
        raise ValueError("LinkedIn refresh response did not contain an access token")
    return payload


def resolve_credentials(
    executor: Mapping[str, Any],
    environ: Mapping[str, str] | None = None,
    *,
    force_refresh: bool = False,
    opener: Callable[..., Any] = urlopen,
) -> Credentials:
    source = executor.get("credential_source", {})
    if not isinstance(source, Mapping):
        raise ValueError("external executor credential_source must be an object")
    access_token, access_origin = secret_value(source, "access_token", environ)
    actor_urn, actor_origin = secret_value(source, "actor_urn", environ)
    if not actor_urn:
        verified = executor.get("verification", {}).get("verified_actor_urn")
        if isinstance(verified, str) and verified:
            actor_urn, actor_origin = verified, "verified-actor"
    client_id, _ = secret_value(source, "client_id", environ)
    client_secret, _ = secret_value(source, "client_secret", environ)
    refresh_token, _ = secret_value(source, "refresh_token", environ)
    refreshed = False
    expires_in = None
    refresh_expires_in = None
    if force_refresh or not access_token:
        refresh = executor.get("token_refresh", {})
        if not isinstance(refresh, Mapping) or refresh.get("mode") != "programmatic":
            raise ValueError("LinkedIn access token is absent and programmatic refresh is unavailable")
        if not all((client_id, client_secret, refresh_token)):
            raise ValueError("LinkedIn programmatic refresh credentials are incomplete")
        payload = refresh_access_token(
            str(client_id), str(client_secret), str(refresh_token), opener=opener
        )
        access_token = str(payload["access_token"])
        access_origin = "programmatic-refresh"
        refreshed = True
        expires_in = int(payload["expires_in"]) if payload.get("expires_in") is not None else None
        refresh_expires_in = (
            int(payload["refresh_token_expires_in"])
            if payload.get("refresh_token_expires_in") is not None
            else None
        )
    if not access_token:
        raise ValueError("LinkedIn access token is unavailable")
    if not actor_urn or not actor_urn.startswith("urn:li:person:"):
        raise ValueError("verified LinkedIn actor URN is unavailable")
    origin = "+".join(value for value in (access_origin, actor_origin) if value)
    return Credentials(
        access_token=access_token,
        actor_urn=actor_urn,
        source=origin or "unknown",
        client_id=client_id,
        client_secret=client_secret,
        refreshed=refreshed,
        expires_in=expires_in,
        refresh_token_expires_in=refresh_expires_in,
    )
