"""Configure a registered Bluesky mirror without posting content."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Callable, Mapping
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.bluesky_handle_lifecycle import resolve_handle
from src.bluesky_mirror_programme import load_registry

Transport = Callable[[str, str, Mapping[str, Any] | None, str], dict[str, Any]]


def xrpc(
    method: str,
    endpoint: str,
    payload: Mapping[str, Any] | None,
    access_jwt: str = "",
    *,
    service_url: str = "https://bsky.social",
) -> dict[str, Any]:
    headers = {"Accept": "application/json"}
    data = None
    url = f"{service_url.rstrip('/')}/xrpc/{endpoint}"
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    if access_jwt:
        headers["Authorization"] = f"Bearer {access_jwt}"
    request = Request(url, data=data, headers=headers, method=method)
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def get_profile_record(
    did: str,
    access_jwt: str,
    *,
    transport: Transport,
) -> dict[str, Any]:
    query = urlencode(
        {"repo": did, "collection": "app.bsky.actor.profile", "rkey": "self"}
    )
    try:
        payload = transport(
            "GET",
            f"com.atproto.repo.getRecord?{query}",
            None,
            access_jwt,
        )
    except HTTPError as error:
        if error.code not in {400, 404}:
            raise
        return {"$type": "app.bsky.actor.profile"}
    value = payload.get("value") or {}
    return dict(value) if isinstance(value, Mapping) else {"$type": "app.bsky.actor.profile"}


def configure_account(
    account: Mapping[str, Any],
    primary_password: str,
    expected_did: str,
    *,
    description: str,
    transport: Transport,
    secret_setter: Callable[[str, str, str], None],
) -> dict[str, Any]:
    handle = str(account["handle"])
    session = transport(
        "POST",
        "com.atproto.server.createSession",
        {"identifier": handle, "password": primary_password},
        "",
    )
    did = str(session.get("did") or "")
    access_jwt = str(session.get("accessJwt") or "")
    if not did or did != expected_did or not access_jwt:
        raise RuntimeError("Authenticated DID does not match the pinned account DID.")

    record = get_profile_record(did, access_jwt, transport=transport)
    record.update(
        {
            "$type": "app.bsky.actor.profile",
            "displayName": str(account["display_name"]),
            "description": description,
            "labels": {
                "$type": "com.atproto.label.defs#selfLabels",
                "values": [{"val": "bot"}],
            },
        }
    )
    transport(
        "POST",
        "com.atproto.repo.putRecord",
        {
            "repo": did,
            "collection": "app.bsky.actor.profile",
            "rkey": "self",
            "record": record,
            "validate": True,
        },
        access_jwt,
    )
    app_password = transport(
        "POST",
        "com.atproto.server.createAppPassword",
        {"name": f"sm-govt-nz-{account['mirror_id']}", "privileged": False},
        access_jwt,
    ).get("password")
    if not app_password:
        raise RuntimeError("Bluesky did not return an app password.")
    secret_setter(str(account["environment"]), "BLUESKY_HANDLE", handle)
    secret_setter(
        str(account["environment"]), "BLUESKY_APP_PASSWORD", str(app_password)
    )
    return {
        "mirror_id": account["mirror_id"],
        "handle": handle,
        "did": did,
        "profile_configured": True,
        "bot_label_configured": True,
        "app_password_configured": True,
        "direct_messages_enabled": False,
        "posting_performed": False,
        "secret_values_recorded": False,
    }


def gh_secret_setter(environment: str, name: str, value: str) -> None:
    subprocess.run(
        [
            "gh",
            "secret",
            "set",
            name,
            "--env",
            environment,
            "--repo",
            "edithatogo/sm-govt-nz",
        ],
        input=value,
        text=True,
        check=True,
        capture_output=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mirror-id", required=True)
    parser.add_argument("--expected-did", required=True)
    parser.add_argument("--official-url", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--registry", default="config/mirror_accounts.json")
    parser.add_argument("--primary-password-env", default="BLUESKY_PRIMARY_PASSWORD")
    args = parser.parse_args()

    password = os.getenv(args.primary_password_env, "")
    if not password:
        raise SystemExit(f"{args.primary_password_env} is required.")
    registry = load_registry(args.registry)
    account = next(
        row for row in registry["mirrors"] if row["mirror_id"] == args.mirror_id
    )
    if not account.get("handle"):
        raise SystemExit("The registry must pin the registered handle first.")
    public_did = resolve_handle(str(account["handle"]))
    if public_did != args.expected_did:
        raise SystemExit("Public handle resolution does not match --expected-did.")
    description = (
        f"{account['profile_disclosure']} Official: {args.official_url} "
        f"Archive: https://huggingface.co/datasets/edithatogo/"
        "corpus-social-media-government-nz"
    )
    if len(description) > 256:
        raise SystemExit("Generated profile description exceeds 256 characters.")
    transport = lambda method, endpoint, payload, token: xrpc(  # noqa: E731
        method, endpoint, payload, token
    )
    report = configure_account(
        account,
        password,
        args.expected_did,
        description=description,
        transport=transport,
        secret_setter=gh_secret_setter,
    )
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
