import argparse
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlencode

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.syndication import JsonHttpClient


def probe_instagram_profile(
    *,
    user_id: str,
    access_token: str,
    api_base_url: str = "https://graph.facebook.com/v20.0",
    client: JsonHttpClient | None = None,
) -> dict:
    http = client or JsonHttpClient()
    query = urlencode(
        {
            "fields": "id,username",
            "access_token": access_token,
        }
    )
    return http.get_json(f"{api_base_url.rstrip('/')}/{user_id}?{query}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe Instagram credentials without posting.")
    parser.add_argument("--json", action="store_true")
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
    safe_profile = {key: profile.get(key) for key in ("id", "username")}
    if args.json:
        print(json.dumps(safe_profile, indent=2, sort_keys=True))
    else:
        print(f"Instagram credential probe passed for @{safe_profile.get('username')} ({safe_profile.get('id')}).")


if __name__ == "__main__":
    main()
