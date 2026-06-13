import argparse
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlencode

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.syndication import JsonHttpClient


def probe_threads_profile(
    *,
    user_id: str,
    access_token: str,
    api_base_url: str = "https://graph.threads.net/v1.0",
    client: JsonHttpClient | None = None,
) -> dict:
    http = client or JsonHttpClient()
    query = urlencode(
        {
            "fields": "id,username,name,threads_profile_picture_url",
            "access_token": access_token,
        }
    )
    return http.get_json(f"{api_base_url.rstrip('/')}/{user_id}?{query}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe Threads credentials without posting.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    user_id = os.getenv("THREADS_USER_ID") or os.getenv("THREADS_MIRROR_ACCOUNT_ID")
    access_token = os.getenv("THREADS_ACCESS_TOKEN")
    if not user_id or not access_token:
        raise SystemExit("Missing THREADS_ACCESS_TOKEN and THREADS_USER_ID.")

    profile = probe_threads_profile(
        user_id=user_id,
        access_token=access_token,
        api_base_url=os.getenv("THREADS_API_BASE_URL", "https://graph.threads.net/v1.0"),
    )
    safe_profile = {key: profile.get(key) for key in ("id", "username", "name")}
    if args.json:
        print(json.dumps(safe_profile, indent=2, sort_keys=True))
    else:
        print(f"Threads credential probe passed for @{safe_profile.get('username')} ({safe_profile.get('id')}).")


if __name__ == "__main__":
    main()
