import argparse
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlencode

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.syndication import JsonHttpClient


def probe_facebook_page(
    *,
    page_id: str,
    page_access_token: str,
    api_base_url: str = "https://graph.facebook.com/v20.0",
    client: JsonHttpClient | None = None,
) -> dict:
    http = client or JsonHttpClient()
    query = urlencode(
        {
            "fields": "id,name,link,tasks,access_token",
            "access_token": page_access_token,
        }
    )
    return http.get_json(f"{api_base_url.rstrip('/')}/{page_id}?{query}")


def safe_page_profile(profile: dict) -> dict:
    return {
        "id": profile.get("id"),
        "name": profile.get("name"),
        "link": profile.get("link"),
        "tasks": profile.get("tasks", []),
        "has_page_access_token": bool(profile.get("access_token")),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe Facebook Page credentials without posting.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    page_id = os.getenv("FACEBOOK_PAGE_ID")
    page_access_token = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
    if not page_id or not page_access_token:
        raise SystemExit("Missing FACEBOOK_PAGE_ACCESS_TOKEN and FACEBOOK_PAGE_ID.")

    profile = probe_facebook_page(
        page_id=page_id,
        page_access_token=page_access_token,
        api_base_url=os.getenv("FACEBOOK_API_BASE_URL", "https://graph.facebook.com/v20.0"),
    )
    safe_profile = safe_page_profile(profile)
    if args.json:
        print(json.dumps(safe_profile, indent=2, sort_keys=True))
    else:
        print(
            "Facebook Page credential probe passed for "
            f"{safe_profile.get('name')} ({safe_profile.get('id')})."
        )


if __name__ == "__main__":
    main()
