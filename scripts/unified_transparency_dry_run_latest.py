import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.bluesky import BlueskyApiClient, normalize_feed_item
from src.config import load_config
from src.syndication import DryRunAdapter
from src.unified_syndication import UnifiedTransparencyAdapter


def build_latest_unified_payload(
    *,
    config_path: str = "config.json",
    feed_client: object | None = None,
) -> dict[str, object]:
    config = load_config(config_path)
    source = config["monitored_accounts"][0]
    target = config["syndication_targets"].get("unified", {})

    client = feed_client or BlueskyApiClient()
    raw_feed = client.fetch_author_feed(source["did"] or source["handle"], limit=1)
    if not raw_feed:
        raise RuntimeError(f"No source posts returned for {source['handle']}.")

    post = normalize_feed_item(raw_feed[0], source["handle"])
    base_target = str(target.get("base_target") or "bluesky")
    base_adapter = DryRunAdapter(base_target)
    adapter = UnifiedTransparencyAdapter(
        base_adapter,
        {source["handle"]: source.get("name", source["handle"])},
    )
    result = adapter.send(post)
    preview_post = base_adapter.sent_posts[0]

    return {
        "dry_run": True,
        "source": {
            "handle": source["handle"],
            "post_id": post["post_id"],
            "created_at": post["created_at"],
            "url": post["url"],
        },
        "target": {
            "platform": "unified",
            "enabled": bool(target.get("enabled", False)),
            "base_target": base_target,
            "historical_replay_enabled": bool(target.get("archive_replay_enabled", False)),
            "gated_by": target.get("gated_by", ""),
        },
        "preview": {
            "base_adapter": base_target,
            "result": {
                "platform": result.platform,
                "success": result.success,
                "skipped": result.skipped,
                "detail": result.detail,
            },
            "post": {
                "post_id": preview_post["post_id"],
                "text": preview_post["text"],
                "url": preview_post["url"],
                "images": preview_post["images"],
            },
        },
    }


def main() -> None:
    print(json.dumps(build_latest_unified_payload(), indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
