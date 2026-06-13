import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.bluesky import BlueskyApiClient, normalize_feed_item


def smoke_check_mirror(
    actor: str,
    *,
    min_posts: int = 1,
    require_original_attribution: bool = True,
    client: BlueskyApiClient | None = None,
) -> dict:
    feed_client = client or BlueskyApiClient()
    raw_feed = feed_client.fetch_author_feed(actor, limit=max(min_posts, 5))
    posts = [normalize_feed_item(item, actor) for item in raw_feed]
    failures: list[str] = []
    if len(posts) < min_posts:
        failures.append(f"expected at least {min_posts} posts, found {len(posts)}")
    if require_original_attribution and posts:
        missing = [post["post_id"] for post in posts[:min_posts] if "Original:" not in post["text"]]
        if missing:
            failures.append(f"missing Original attribution in posts: {', '.join(missing)}")
    return {
        "actor": actor,
        "checked_posts": min(len(posts), min_posts),
        "latest_post_url": posts[0]["url"] if posts else "",
        "valid": not failures,
        "failures": failures,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke check the public Bluesky mirror feed.")
    parser.add_argument("--actor", default="mirnzcourts.bsky.social")
    parser.add_argument("--min-posts", type=int, default=1)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = smoke_check_mirror(args.actor, min_posts=args.min_posts)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    elif result["valid"]:
        print(f"Bluesky mirror smoke check passed: {result['latest_post_url']}")
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
