import json

from scripts.archive_rss_history import archive_rss_history


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


def test_archive_rss_history_writes_raw_normalized_and_report(tmp_path):
    feed_report = tmp_path / "feeds.json"
    feed_report.write_text(
        json.dumps({"feeds": [{"feed_url": "https://example.test/feed.xml"}]}),
        encoding="utf-8",
    )
    parser = FakeParser()

    report = archive_rss_history(
        feed_report_path=feed_report,
        raw_root=tmp_path / "raw",
        normalized_root=tmp_path / "normalized",
        report_path=tmp_path / "report.json",
        parser=parser,
    )

    assert parser.url == "https://example.test/feed.xml"
    assert report["archived_count"] == 1
    assert list((tmp_path / "raw" / "2026-06").glob("*.json"))
    normalized = list((tmp_path / "normalized").glob("*.jsonl"))[0].read_text(encoding="utf-8")
    assert json.loads(normalized)["canonical_url"] == "https://example.test/judgment"
    assert json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))["feed_count"] == 1
