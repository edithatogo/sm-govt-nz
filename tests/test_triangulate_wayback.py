import json
from io import BytesIO

from scripts.triangulate_wayback import query_wayback, triangulate


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps([
            ["timestamp", "original", "statuscode", "mimetype", "digest"],
            ["20250101000000", "https://example.govt.nz/", "200", "text/html", "abc"],
        ]).encode()


def test_query_wayback_parses_compact_cdx_rows():
    result = query_wayback("https://example.govt.nz/", opener=lambda request, timeout: FakeResponse())
    assert result == [{
        "timestamp": "20250101000000",
        "original": "https://example.govt.nz/",
        "statuscode": "200",
        "mimetype": "text/html",
        "digest": "abc",
    }]


def test_triangulation_is_metadata_only_and_reports_unsupported_urls(monkeypatch):
    monkeypatch.setattr(
        "scripts.triangulate_wayback.query_wayback",
        lambda url: [{"timestamp": "20250101000000", "original": url}],
    )
    report = triangulate({"sources": [
        {"source_id": "web", "platform": "website_page", "url": "https://example.govt.nz/"},
        {"source_id": "invalid", "platform": "unknown", "url": "mailto:test@example.govt.nz"},
    ]), limit=10, delay=0)
    assert report["snapshot_downloaded"] is False
    assert report["summary"] == {
        "sources_checked": 2,
        "capture_metadata_sources": 1,
        "no_capture_sources": 0,
        "provider_errors": 0,
    }
    assert report["sources"][1]["wayback_status"] == "unsupported_url"
