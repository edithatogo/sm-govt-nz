from typing import Any, Mapping

from src.bluesky import (
    build_post_url,
    extract_post_id,
    fetch_new_posts_for_account,
    normalize_feed_item,
)
from src.config import MonitoredAccount


class FakeFeedClient:
    def __init__(self, feed: list[Mapping[str, Any]]) -> None:
        self.feed = feed
        self.requested_actor = ""
        self.requested_limit = 0

    def fetch_author_feed(self, actor: str, *, limit: int = 50) -> list[Mapping[str, Any]]:
        self.requested_actor = actor
        self.requested_limit = limit
        return self.feed


def test_extract_post_id_from_at_uri() -> None:
    uri = "at://did:plc:123/app.bsky.feed.post/3ksy5q7xabc2"

    assert extract_post_id(uri) == "3ksy5q7xabc2"
    assert build_post_url("agency.bsky.social", uri).endswith(
        "/profile/agency.bsky.social/post/3ksy5q7xabc2"
    )


def test_normalize_feed_item_preserves_text_metadata_and_images() -> None:
    item = make_feed_item(
        post_id="new-post",
        text="Official update",
        created_at="2026-06-10T00:00:00Z",
        images=[
            {
                "alt": "Accessible image description",
                "fullsize": "https://cdn.example/full.jpg",
                "thumb": "https://cdn.example/thumb.jpg",
            }
        ],
    )

    post = normalize_feed_item(item, "fallback.bsky.social")

    assert post["post_id"] == "new-post"
    assert post["handle"] == "agency.bsky.social"
    assert post["text"] == "Official update"
    assert post["created_at"] == "2026-06-10T00:00:00Z"
    assert post["images"][0]["alt"] == "Accessible image description"
    assert post["url"] == "https://bsky.app/profile/agency.bsky.social/post/new-post"


def test_fetch_new_posts_stops_at_last_seen_and_returns_oldest_first() -> None:
    account: MonitoredAccount = {
        "handle": "agency.bsky.social",
        "did": "did:plc:agency",
        "name": "Agency",
        "syndicate_to": ["discord"],
    }
    client = FakeFeedClient(
        [
            make_feed_item("post-3", "Newest"),
            make_feed_item("post-2", "Middle"),
            make_feed_item("post-1", "Already processed"),
            make_feed_item("post-0", "Older"),
        ]
    )

    posts = fetch_new_posts_for_account(
        account,
        last_seen_post_id="post-1",
        client=client,
        limit=25,
    )

    assert client.requested_actor == "did:plc:agency"
    assert client.requested_limit == 25
    assert [post["post_id"] for post in posts] == ["post-2", "post-3"]


def test_fetch_new_posts_uses_handle_when_did_is_missing() -> None:
    account: MonitoredAccount = {
        "handle": "agency.bsky.social",
        "did": "",
        "name": "Agency",
        "syndicate_to": ["discord"],
    }
    client = FakeFeedClient([make_feed_item("post-1", "Only post")])

    posts = fetch_new_posts_for_account(account, client=client)

    assert client.requested_actor == "agency.bsky.social"
    assert posts[0]["post_id"] == "post-1"


def make_feed_item(
    post_id: str,
    text: str,
    created_at: str = "2026-06-10T00:00:00Z",
    images: list[Mapping[str, str]] | None = None,
) -> Mapping[str, Any]:
    return {
        "post": {
            "uri": f"at://did:plc:agency/app.bsky.feed.post/{post_id}",
            "cid": f"cid-{post_id}",
            "author": {
                "did": "did:plc:agency",
                "handle": "agency.bsky.social",
            },
            "record": {
                "text": text,
                "createdAt": created_at,
            },
            "embed": {
                "images": list(images or []),
            },
        }
    }