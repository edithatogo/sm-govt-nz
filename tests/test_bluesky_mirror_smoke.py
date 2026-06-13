from scripts.bluesky_mirror_smoke import smoke_check_mirror


class FakeFeedClient:
    def __init__(self, text: str) -> None:
        self.text = text

    def fetch_author_feed(self, actor, *, limit=50):
        return [
            {
                "post": {
                    "uri": f"at://did:plc:mirror/app.bsky.feed.post/post-{index}",
                    "cid": "cid",
                    "author": {"handle": actor, "did": "did:plc:mirror"},
                    "record": {"text": self.text, "createdAt": "2026-06-13T00:00:00Z"},
                }
            }
            for index in range(limit)
        ]


def test_smoke_check_accepts_original_attribution() -> None:
    result = smoke_check_mirror(
        "mirnzcourts.bsky.social",
        client=FakeFeedClient("Court notice\n\nOriginal: https://example.test"),
    )

    assert result["valid"] is True
    assert result["latest_post_url"].endswith("/post-0")


def test_smoke_check_rejects_missing_original_attribution() -> None:
    result = smoke_check_mirror(
        "mirnzcourts.bsky.social",
        client=FakeFeedClient("Court notice"),
    )

    assert result["valid"] is False
    assert result["failures"]
