from src.feed_ingestion import fetch_feed_posts, normalize_feed_entry


class FakeFeed:
    entries = [
        {
            "title": "Second update",
            "summary": "Later",
            "link": "https://example.test/two",
            "published": "Wed, 10 Jun 2026 01:00:00 GMT",
        },
        {
            "title": "First update",
            "summary": "Earlier",
            "link": "https://example.test/one",
            "published": "Wed, 10 Jun 2026 00:00:00 GMT",
        },
    ]


class FakeParser:
    def parse(self, url):
        self.url = url
        return FakeFeed()


def test_normalize_feed_entry_builds_stable_post_contract() -> None:
    post = normalize_feed_entry(
        {"title": "Release", "summary": "Details", "link": "https://example.test/release"},
        source_id="agency-rss",
        feed_url="https://example.test/feed.xml",
    )

    assert post["handle"] == "agency-rss"
    assert post["text"] == "Release\n\nDetails"
    assert post["url"] == "https://example.test/release"
    assert len(post["post_id"]) == 24


def test_fetch_feed_posts_returns_oldest_first() -> None:
    parser = FakeParser()

    posts = fetch_feed_posts("https://example.test/feed.xml", source_id="agency-rss", parser=parser)

    assert parser.url == "https://example.test/feed.xml"
    assert [post["url"] for post in posts] == ["https://example.test/one", "https://example.test/two"]
