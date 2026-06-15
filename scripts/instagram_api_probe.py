import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.syndication import JsonHttpClient


INSTAGRAM_PROFILE_FIELDS = "id,username,account_type,media_count,name,is_business"


def probe_instagram_profile(
    *,
    user_id: str,
    access_token: str,
    api_base_url: str = "https://graph.facebook.com/v20.0",
    client: JsonHttpClient | None = None,
) -> dict[str, Any]:
    """Probe the Instagram Graph API for profile identity without posting.

    Returns the raw API response containing fields like id, username,
    account_type, media_count, etc.
    """
    http = client or JsonHttpClient()
    query = urlencode(
        {
            "fields": INSTAGRAM_PROFILE_FIELDS,
            "access_token": access_token,
        }
    )
    return http.get_json(f"{api_base_url.rstrip('/')}/{user_id}?{query}")



def safe_profile_summary(profile: dict[str, Any]) -> dict[str, Any]:
    """Extract a safe summary from the raw API profile response."""
    return {
        "id": profile.get("id"),
        "username": profile.get("username"),
        "account_type": profile.get("account_type"),
        "name": profile.get("name"),
        "media_count": profile.get("media_count"),
        "is_business": profile.get("is_business"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe Instagram credentials without posting.")
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--error-only",
        action="store_true",
        help="Only print error details if probe fails.",
    )
    args = parser.parse_args()

    user_id = os.getenv("INSTAGRAM_USER_ID")
    access_token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
    if not user_id or not access_token:
        raise SystemExit("Missing INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_USER_ID.")

    profile = probe_instagram_profile(
        user_id=user_id,
        access_token=access_token,
        api_base_url=os.getenv("INSTAGRAM_API_BASE_URL", "https://graph.facebook.com/v20.0"),
    )

    # Check for API error response
    if "error" in profile:
        error = profile["error"]
        code = error.get("code", "unknown")
        message = error.get("message", "Unknown error")
        error_msg = f"Instagram probe failed (error {code}): {message}"
        if args.error_only or args.json:
            error_output = {
                "success": False,
                "error_code": code,
                "error_message": message,
                "user_id": user_id,
            }
            print(json.dumps(error_output, indent=2, sort_keys=True))
        else:
            print(error_msg)
        raise SystemExit(1)

    safe = safe_profile_summary(profile)
    if args.json:
        print(json.dumps(safe, indent=2, sort_keys=True))
    else:
        account_type = safe.get("account_type", "unknown")
        if account_type in ("BUSINESS", "CREATOR"):
            status = "Professional account confirmed"
        else:
            status = f"Account type is '{account_type}' — Professional (Business/Creator) required for API publishing"
        print(
            f"Instagram credential probe passed for @{safe.get('username')} ({safe.get('id')}). "
            f"{status}"
        )


if __name__ == "__main__":
    main()
