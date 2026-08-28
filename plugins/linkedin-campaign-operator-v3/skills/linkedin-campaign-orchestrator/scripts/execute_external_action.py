#!/usr/bin/env python3
"""Execute one idempotent LinkedIn mutation through the verified official API adapter."""

from __future__ import annotations

import argparse
import json
import mimetypes
import socket
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from executor_readiness import normalize_action_class, task_readiness
from credential_manager import resolve_credentials


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def append_event(path: Path, event: Mapping[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(event), ensure_ascii=False) + "\n")


def prior_outcome(path: Path, idempotency_key: str) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    latest = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if isinstance(value, dict) and value.get("idempotency_key") == idempotency_key:
            latest = value
    return latest


def request_parts(action: Mapping[str, Any], actor_urn: str) -> tuple[str, dict[str, Any]]:
    action_class = normalize_action_class(action.get("action_class") or action.get("action_type"))
    text = action.get("text") or action.get("commentary")
    if action_class == "publication":
        if not isinstance(text, str) or not text.strip():
            raise ValueError("publication requires non-empty text")
        body: dict[str, Any] = {
            "author": actor_urn,
            "commentary": text,
            "visibility": action.get("visibility", "PUBLIC"),
            "distribution": action.get(
                "distribution",
                {
                    "feedDistribution": "MAIN_FEED",
                    "targetEntities": [],
                    "thirdPartyDistributionChannels": [],
                },
            ),
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": bool(
                action.get("is_reshare_disabled_by_author", False)
            ),
        }
        if isinstance(action.get("content"), Mapping):
            body["content"] = dict(action["content"])
        return "/rest/posts", body
    if action_class in {"comment", "reply"}:
        target = action.get("target_urn")
        object_urn = action.get("object_urn")
        if not isinstance(target, str) or not target.startswith("urn:li:"):
            raise ValueError(f"{action_class} requires target_urn")
        if not isinstance(object_urn, str) or not object_urn.startswith("urn:li:"):
            raise ValueError(f"{action_class} requires object_urn")
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"{action_class} requires non-empty text")
        body = {"actor": actor_urn, "object": object_urn, "message": {"text": text}}
        if action_class == "reply":
            parent = action.get("parent_comment_urn") or target
            if not isinstance(parent, str) or not parent.startswith("urn:li:comment:"):
                raise ValueError("reply requires parent_comment_urn or a comment target_urn")
            body["parentComment"] = parent
        return f"/rest/socialActions/{quote(target, safe='')}/comments", body
    if action_class == "reaction":
        target = action.get("target_urn")
        if not isinstance(target, str) or not target.startswith("urn:li:"):
            raise ValueError("reaction requires target_urn")
        reaction_type = str(action.get("reaction_type") or "LIKE").upper()
        if reaction_type not in {
            "LIKE", "PRAISE", "EMPATHY", "INTEREST", "APPRECIATION", "ENTERTAINMENT"
        }:
            raise ValueError(f"unsupported LinkedIn reaction type: {reaction_type}")
        return f"/rest/reactions?actor={quote(actor_urn, safe='')}", {
            "root": action.get("root_urn") or action.get("object_urn") or target,
            "reactionType": reaction_type,
        }
    raise ValueError(f"unsupported autonomous action class: {action_class}")


def api_request(
    method: str,
    url: str,
    token: str,
    api_version: str,
    body: Mapping[str, Any] | None = None,
) -> tuple[int, dict[str, str], Any]:
    encoded = None if body is None else json.dumps(dict(body)).encode("utf-8")
    request = Request(
        url,
        data=encoded,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Linkedin-Version": api_version,
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
        },
    )
    with urlopen(request, timeout=30) as response:
        raw = response.read().decode("utf-8")
        parsed = json.loads(raw) if raw.strip() else None
        return response.status, {key.lower(): value for key, value in response.headers.items()}, parsed


def upload_image(
    media_path: Path,
    actor_urn: str,
    api_base: str,
    token: str,
    api_version: str,
) -> str:
    if not media_path.is_file():
        raise ValueError(f"publication media file does not exist: {media_path}")
    status, _, payload = api_request(
        "POST",
        api_base + "/rest/images?action=initializeUpload",
        token,
        api_version,
        {"initializeUploadRequest": {"owner": actor_urn}},
    )
    value = payload.get("value", {}) if isinstance(payload, Mapping) else {}
    upload_url = value.get("uploadUrl") if isinstance(value, Mapping) else None
    image_urn = value.get("image") if isinstance(value, Mapping) else None
    if status != 200 or not isinstance(upload_url, str) or not isinstance(image_urn, str):
        raise ValueError("LinkedIn image initialization did not return an upload URL and image URN")
    media_bytes = media_path.read_bytes()
    content_type = mimetypes.guess_type(media_path.name)[0] or "application/octet-stream"
    request = Request(
        upload_url,
        data=media_bytes,
        method="PUT",
        headers={"Authorization": f"Bearer {token}", "Content-Type": content_type},
    )
    with urlopen(request, timeout=60) as response:
        if response.status not in {200, 201}:
            raise ValueError(f"LinkedIn image upload returned HTTP {response.status}")
    image_path = f"/rest/images/{quote(image_urn, safe='')}"
    for _ in range(15):
        image_status, _, image_body = api_request(
            "GET", api_base + image_path, token, api_version
        )
        state = image_body.get("status") if isinstance(image_body, Mapping) else None
        if image_status == 200 and state == "AVAILABLE":
            return image_urn
        if state == "PROCESSING_FAILED":
            raise ValueError("LinkedIn image processing failed")
        time.sleep(2)
    raise TimeoutError("LinkedIn image did not become available before the verification timeout")


def verify_action(
    action: Mapping[str, Any],
    actor_urn: str,
    create_headers: Mapping[str, str],
    create_body: Any,
    api_base: str,
    token: str,
    api_version: str,
) -> dict[str, Any]:
    action_class = normalize_action_class(action.get("action_class") or action.get("action_type"))
    if action_class == "publication":
        resource_id = create_headers.get("x-restli-id")
        if not resource_id:
            raise ValueError("LinkedIn did not return x-restli-id for publication")
        path = f"/rest/posts/{quote(resource_id, safe='')}?viewContext=AUTHOR"
        status, _, body = api_request("GET", api_base + path, token, api_version)
        return {"verified": status == 200 and isinstance(body, dict), "resource_id": resource_id}
    if action_class in {"comment", "reply"}:
        comment_id = create_body.get("id") if isinstance(create_body, Mapping) else None
        target = action.get("target_urn")
        if not comment_id or not isinstance(target, str):
            raise ValueError("LinkedIn did not return a comment id")
        path = f"/rest/socialActions/{quote(target, safe='')}/comments/{quote(str(comment_id), safe='')}"
        status, _, body = api_request("GET", api_base + path, token, api_version)
        return {"verified": status == 200 and isinstance(body, dict), "resource_id": str(comment_id)}
    if action_class == "reaction":
        target = action.get("target_urn")
        if not isinstance(target, str):
            raise ValueError("reaction requires target_urn")
        key = f"(actor:{actor_urn},entity:{target})"
        path = f"/rest/reactions/{quote(key, safe='(),')}"
        status, _, body = api_request("GET", api_base + path, token, api_version)
        visible = isinstance(body, Mapping) and body.get("root") in {
            target, action.get("root_urn"), action.get("object_urn")
        }
        return {
            "verified": status == 200 and visible,
            "resource_id": body.get("id") if isinstance(body, Mapping) else target,
        }
    raise ValueError(f"cannot verify action class: {action_class}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state_dir", type=Path)
    parser.add_argument("action_json", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    state_dir = args.state_dir.expanduser().resolve()
    action_path = args.action_json.expanduser().resolve()
    events_path = state_dir / "external-executor-events.jsonl"
    public_mutation_started = False
    try:
        action = load_object(action_path)
        executor = load_object(state_dir / "external-executor.json")
        idempotency_key = action.get("idempotency_key")
        if not isinstance(idempotency_key, str) or not idempotency_key:
            raise ValueError("action requires idempotency_key")
        previous = prior_outcome(events_path, idempotency_key)
        if previous and previous.get("outcome") == "verified":
            print(json.dumps({"valid": True, "decision": "already-verified", "event": previous}))
            return 0
        if previous and previous.get("outcome") in {"attempting", "ambiguous"}:
            raise ValueError("prior action outcome is ambiguous; automatic retry is forbidden")
        readiness = task_readiness(
            {"action_type": action.get("action_class") or action.get("action_type")},
            executor,
        )
        if not readiness["unattended_ready"]:
            print(json.dumps({"valid": False, "readiness": readiness}, indent=2))
            return 2
        credentials = resolve_credentials(executor)
        token = credentials.access_token
        actor_urn = credentials.actor_urn
        path, body = request_parts(action, actor_urn)
        if args.dry_run:
            print(json.dumps({
                "valid": True,
                "decision": "dry-run",
                "method": "POST",
                "path": path,
                "body": body,
                "idempotency_key": idempotency_key,
            }, indent=2, ensure_ascii=False))
            return 0
        api_base = str(executor.get("api_base_url") or "https://api.linkedin.com").rstrip("/")
        api_version = str(executor.get("api_version") or "202608")
        if normalize_action_class(action.get("action_class") or action.get("action_type")) == "publication":
            media_file = action.get("media_file")
            if isinstance(media_file, str) and media_file:
                media_path = Path(media_file).expanduser()
                if not media_path.is_absolute():
                    media_path = state_dir / media_path
                image_urn = upload_image(
                    media_path.resolve(), actor_urn, api_base, token, api_version
                )
                body["content"] = {
                    "media": {
                        "id": image_urn,
                        "altText": str(action.get("alt_text") or "")[:4086],
                    }
                }
        now = datetime.now(timezone.utc).isoformat()
        append_event(events_path, {
            "idempotency_key": idempotency_key,
            "action_class": normalize_action_class(action.get("action_class") or action.get("action_type")),
            "attempted_at": now,
            "outcome": "attempting",
        })
        public_mutation_started = True
        status, headers, response_body = api_request(
            "POST", api_base + path, token, api_version, body
        )
        verification = verify_action(
            action,
            actor_urn,
            headers,
            response_body,
            api_base,
            token,
            api_version,
        )
        outcome = "verified" if verification["verified"] else "ambiguous"
        event = {
            "idempotency_key": idempotency_key,
            "action_class": normalize_action_class(action.get("action_class") or action.get("action_type")),
            "attempted_at": now,
            "http_status": status,
            "outcome": outcome,
            "resource_id": verification.get("resource_id"),
        }
        append_event(events_path, event)
        print(json.dumps({"valid": outcome == "verified", "event": event}, indent=2))
        return 0 if outcome == "verified" else 3
    except HTTPError as exc:
        if (
            public_mutation_started
            and exc.code >= 500
            and "idempotency_key" in locals()
            and isinstance(idempotency_key, str)
        ):
            append_event(events_path, {
                "idempotency_key": idempotency_key,
                "attempted_at": datetime.now(timezone.utc).isoformat(),
                "outcome": "ambiguous",
                "error_class": f"LinkedInHTTP{exc.code}",
            })
            print(
                json.dumps({"valid": False, "error": "LinkedIn server outcome ambiguous"}),
                file=sys.stderr,
            )
            return 3
        print(json.dumps({"valid": False, "error": f"LinkedIn HTTP {exc.code}"}), file=sys.stderr)
        return 1
    except (URLError, socket.timeout, TimeoutError) as exc:
        if (
            public_mutation_started
            and "idempotency_key" in locals()
            and isinstance(idempotency_key, str)
        ):
            append_event(events_path, {
                "idempotency_key": idempotency_key,
                "attempted_at": datetime.now(timezone.utc).isoformat(),
                "outcome": "ambiguous",
                "error_class": type(exc).__name__,
            })
        print(json.dumps({"valid": False, "error": "network outcome ambiguous"}), file=sys.stderr)
        return 3
    except (KeyError, OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
