import json
from pathlib import Path

from scripts.archive_current_sources import archive_current_sources


class FakeFeed:
    entries = [
        {
            "title": "Judgment",
            "summary": "Published",
            "link": "https://example.test/judgment",
            "published": "Wed, 10 Jun 2026 01:00:00 GMT",
        }
    ]


class FakeParser:
    def parse(self, url):
        self.url = url
        return FakeFeed()


def test_archive_current_sources_writes_bluesky_rss_and_archive_state(tmp_path):
    feed_config = tmp_path / "feeds.json"
    feed_config.write_text(
        json.dumps({"feeds": [{"feed_url": "https://example.test/feed.xml"}]}),
        encoding="utf-8",
    )

    report = archive_current_sources(
        feed_config_path=feed_config,
        archive_state_path=tmp_path / "archive_state.json",
        health_report_path=tmp_path / "archive_source_health.json",
        raw_root=tmp_path / "raw",
        normalized_root=tmp_path / "normalized",
        bluesky_fetcher=lambda actor: [
            {
                "post_id": "abc123",
                "uri": "at://did/post/abc123",
                "cid": "cid123",
                "handle": "courtsofnz.bsky.social",
                "text": "Court update",
                "created_at": "2026-06-10T00:00:00+00:00",
                "url": "https://bsky.app/profile/courtsofnz.bsky.social/post/abc123",
                "images": [],
            }
        ],
        parser=FakeParser(),
    )

    assert report["archive_only"] is True
    assert report["archived_counts"] == {"bluesky": 1, "rss": 1}
    assert (tmp_path / "raw" / "bluesky" / "2026-06" / "abc123.json").is_file()
    assert list((tmp_path / "raw" / "rss" / "2026-06").glob("*.json"))
    assert "bluesky:abc123" in (tmp_path / "normalized" / "bluesky" / "2026-06.jsonl").read_text(
        encoding="utf-8"
    )
    assert "rss:" in (tmp_path / "normalized" / "rss" / "2026-06.jsonl").read_text(
        encoding="utf-8"
    )
    state = json.loads((tmp_path / "archive_state.json").read_text(encoding="utf-8"))
    assert state["source_cursors"]["courts-nz-bluesky"] == "abc123"
    assert "courts-nz-rss-website" in state["source_cursors"]


def test_archive_current_sources_preserves_existing_capture_timestamp(tmp_path):
    feed_config = tmp_path / "feeds.json"
    feed_config.write_text(json.dumps({"feeds": []}), encoding="utf-8")
    raw_post = tmp_path / "raw" / "bluesky" / "2026-06" / "abc123.json"
    raw_post.parent.mkdir(parents=True)
    raw_post.write_text(
        json.dumps(
            {
                "captured_at": "2026-06-10T00:00:00+00:00",
                "post": {"post_id": "abc123"},
            }
        ),
        encoding="utf-8",
    )

    archive_current_sources(
        feed_config_path=feed_config,
        archive_state_path=tmp_path / "archive_state.json",
        health_report_path=tmp_path / "archive_source_health.json",
        raw_root=tmp_path / "raw",
        normalized_root=tmp_path / "normalized",
        bluesky_fetcher=lambda actor: [
            {
                "post_id": "abc123",
                "uri": "at://did/post/abc123",
                "cid": "cid123",
                "handle": "courtsofnz.bsky.social",
                "text": "Court update",
                "created_at": "2026-06-10T00:00:00+00:00",
                "url": "https://bsky.app/profile/courtsofnz.bsky.social/post/abc123",
                "images": [],
            }
        ],
        include_rss=False,
    )

    shard = Path(tmp_path / "normalized" / "bluesky" / "2026-06.jsonl")
    record = json.loads(shard.read_text(encoding="utf-8"))
    assert record["captured_at"] == "2026-06-10T00:00:00+00:00"


def test_archive_current_sources_keeps_health_file_stable_for_noop_run(tmp_path):
    feed_config = tmp_path / "feeds.json"
    feed_config.write_text(json.dumps({"feeds": []}), encoding="utf-8")
    kwargs = {
        "feed_config_path": feed_config,
        "archive_state_path": tmp_path / "archive_state.json",
        "health_report_path": tmp_path / "archive_source_health.json",
        "raw_root": tmp_path / "raw",
        "normalized_root": tmp_path / "normalized",
        "bluesky_fetcher": lambda actor: [
            {
                "post_id": "abc123",
                "uri": "at://did/post/abc123",
                "cid": "cid123",
                "handle": "courtsofnz.bsky.social",
                "text": "Court update",
                "created_at": "2026-06-10T00:00:00+00:00",
                "url": "https://bsky.app/profile/courtsofnz.bsky.social/post/abc123",
                "images": [],
            }
        ],
    }

    archive_current_sources(**kwargs)
    first_health = (tmp_path / "archive_source_health.json").read_text(encoding="utf-8")
    archive_current_sources(**kwargs)
    second_health = (tmp_path / "archive_source_health.json").read_text(encoding="utf-8")

    assert second_health == first_health
