import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.bluesky import BlueskyApiClient, normalize_feed_item
from src.config import load_config
from src.syndication import FacebookPageAdapter


def build_latest_facebook_payload(
    *,
    config_path: str = "config.json",
    api_base_url: str = "https://graph.facebook.com/v20.0",
    feed_client: object | None = None,
) -> dict[str, object]:
    config = load_config(config_path)
    source = config["monitored_accounts"][0]
    target = config["syndication_targets"].get("facebook", {})
    page_id = os.getenv("FACEBOOK_PAGE_ID") or "FACEBOOK_PAGE_ID"
    page_access_token = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN") or "FACEBOOK_PAGE_ACCESS_TOKEN"

    client = feed_client or BlueskyApiClient()
    raw_feed = client.fetch_author_feed(source["did"] or source["handle"], limit=1)
    if not raw_feed:
        raise RuntimeError(f"No source posts returned for {source['handle']}.")

    post = normalize_feed_item(raw_feed[0], source["handle"])
    adapter = FacebookPageAdapter(
        page_id,
        page_access_token,
        api_base_url=api_base_url,
    )
    url, form = adapter.publish_request(post)

    return {
        "dry_run": True,
        "source": {
            "handle": source["handle"],
            "post_id": post["post_id"],
            "created_at": post["created_at"],
            "url": post["url"],
        },
        "target": {
            "platform": "facebook",
            "account_handle": target.get("account_handle", ""),
            "profile_url": target.get("profile_url", ""),
            "enabled": bool(target.get("enabled", False)),
            "historical_replay_enabled": bool(target.get("archive_replay_enabled", False)),
        },
        "request": {
            "method": "POST",
            "url": url,
            "form": _redact(form),
        },
    }


def main() -> None:
    print(json.dumps(build_latest_facebook_payload(), indent=2, ensure_ascii=False, sort_keys=True))


def _redact(payload: dict[str, str]) -> dict[str, str]:
    redacted = dict(payload)
    if "access_token" in redacted:
        redacted["access_token"] = "<redacted>"
    return redacted


if __name__ == "__main__":
    main()
