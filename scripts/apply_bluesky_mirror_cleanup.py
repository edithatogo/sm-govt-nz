"""Apply an exact, pre-approved Bluesky mirror cleanup packet."""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.request import Request, urlopen

from src.bluesky import BlueskyApiClient, extract_post_id
from src.bluesky_mirror_programme import (
    BLUESKY_APP_PASSWORD_PATTERN,
    load_registry,
)


def apply_cleanup(
    *,
    registry_path: str | Path,
    report_path: str | Path,
    mirror_id: str,
    approved_uris: list[str],
    apply: bool,
    visible_lookup: Callable[[list[str]], set[str]] | None = None,
    deleter: Callable[[Mapping[str, Any], list[str]], None] | None = None,
) -> dict[str, Any]:
    registry = load_registry(registry_path)
    account = next(
        row for row in registry["mirrors"] if row.get("mirror_id") == mirror_id
    )
    report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    if report.get("mirror_id") != mirror_id:
        raise ValueError("Cleanup report mirror_id does not match.")
    packet = report.get("cleanup_approval_packet")
    if not isinstance(packet, Mapping) or not packet.get(
        "requires_exact_uri_approval"
    ):
        raise ValueError("Cleanup report does not require exact URI approval.")
    candidates = {
        str(item.get("uri") or ""): item
        for item in packet.get("candidates", [])
        if isinstance(item, Mapping)
    }
    if not approved_uris:
        raise ValueError("At least one exact approved URI is required.")
    if len(set(approved_uris)) != len(approved_uris):
        raise ValueError("Approved URIs must be unique.")

    account_did = str(account.get("account_did") or "")
    for uri in approved_uris:
        if uri not in candidates:
            raise ValueError(f"URI is absent from the cleanup packet: {uri}")
        if _uri_did(uri) != account_did:
            raise ValueError(f"URI is not owned by the selected mirror DID: {uri}")

    lookup = visible_lookup or _visible_uris
    visible = lookup(approved_uris)
    unapproved_visible = visible - set(approved_uris)
    if unapproved_visible:
        raise ValueError("Visibility lookup returned an unapproved URI.")
    to_delete = sorted(visible)
    already_missing = sorted(set(approved_uris) - visible)
    if apply and to_delete:
        if deleter is None:
            deleter = authenticated_delete
        deleter(account, to_delete)

    return {
        "schema_version": 1,
        "mirror_id": mirror_id,
        "evaluated_at": datetime.now(UTC).isoformat(),
        "apply_requested": apply,
        "approved_uris": sorted(approved_uris),
        "candidate_reasons": {
            uri: sorted(str(value) for value in candidates[uri].get("reasons", []))
            for uri in sorted(approved_uris)
        },
        "visible_before_apply": to_delete,
        "already_missing": already_missing,
        "delete_requests_succeeded": to_delete if apply else [],
        "status": "apply_completed" if apply else "dry_run",
        "credential_material_recorded": False,
    }


def authenticated_delete(account: Mapping[str, Any], uris: list[str]) -> None:
    handle = os.environ.get("BLUESKY_HANDLE", "")
    app_password = os.environ.get("BLUESKY_APP_PASSWORD", "")
    expected_handle = str(account.get("handle") or "")
    expected_did = str(account.get("account_did") or "")
    if handle != expected_handle:
        raise ValueError("BLUESKY_HANDLE does not match the selected mirror.")
    if not BLUESKY_APP_PASSWORD_PATTERN.fullmatch(app_password):
        raise ValueError("BLUESKY_APP_PASSWORD is not an app password.")

    service = os.environ.get("BLUESKY_SERVICE_URL", "https://bsky.social").rstrip("/")
    session = _post_json(
        f"{service}/xrpc/com.atproto.server.createSession",
        {"identifier": handle, "password": app_password},
    )
    if str(session.get("did") or "") != expected_did:
        raise ValueError("Authenticated DID does not match the selected mirror.")
    access_token = str(session.get("accessJwt") or "")
    if not access_token:
        raise ValueError("Bluesky session did not return an access token.")

    for uri in uris:
        _post_json(
            f"{service}/xrpc/com.atproto.repo.deleteRecord",
            {
                "repo": expected_did,
                "collection": "app.bsky.feed.post",
                "rkey": extract_post_id(uri),
            },
            access_token=access_token,
        )


def _post_json(
    url: str,
    payload: Mapping[str, Any],
    *,
    access_token: str = "",
) -> dict[str, Any]:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urlopen(request, timeout=30) as response:
        body = response.read().decode("utf-8")
    return json.loads(body) if body else {}


def _visible_uris(uris: list[str]) -> set[str]:
    return {
        str(post.get("uri") or "")
        for post in BlueskyApiClient(timeout_seconds=15).fetch_posts(uris)
        if post.get("uri")
    }


def _uri_did(uri: str) -> str:
    parts = uri.split("/")
    if len(parts) < 3 or parts[0] != "at:" or not parts[2].startswith("did:"):
        return ""
    return parts[2]


def _approved_uris(raw: str) -> list[str]:
    value = json.loads(raw)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError("approved-uris-json must be a JSON array of strings.")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mirror-id", required=True)
    parser.add_argument(
        "--registry",
        default="config/mirror_accounts.json",
    )
    parser.add_argument("--report", required=True)
    parser.add_argument("--approved-uris-json", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    result = apply_cleanup(
        registry_path=args.registry,
        report_path=args.report,
        mirror_id=args.mirror_id,
        approved_uris=_approved_uris(args.approved_uris_json),
        apply=args.apply,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
