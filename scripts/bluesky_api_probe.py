import argparse
import json
import os
from urllib.request import Request, urlopen


def validate_session(handle: str, app_password: str, *, service_url: str) -> dict:
    payload = json.dumps({"identifier": handle, "password": app_password}).encode("utf-8")
    request = Request(
        f"{service_url.rstrip('/')}/xrpc/com.atproto.server.createSession",
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate Bluesky mirror credentials without posting content."
    )
    parser.add_argument("--handle", default=os.getenv("BLUESKY_MIRROR_HANDLE", ""))
    parser.add_argument(
        "--app-password",
        default=os.getenv("BLUESKY_MIRROR_APP_PASSWORD", ""),
    )
    parser.add_argument(
        "--service-url",
        default=os.getenv("BLUESKY_SERVICE_URL", "https://bsky.social"),
    )
    args = parser.parse_args()

    if not args.handle or not args.app_password:
        raise SystemExit("BLUESKY_MIRROR_HANDLE and BLUESKY_MIRROR_APP_PASSWORD are required.")

    session = validate_session(args.handle, args.app_password, service_url=args.service_url)
    print(
        json.dumps(
            {
                "handle": session.get("handle"),
                "did": session.get("did"),
                "valid": True,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
