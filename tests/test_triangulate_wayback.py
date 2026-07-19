import json
from pathlib import Path

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
    ]}, limit=10, delay=0)
    assert report["snapshot_downloaded"] is False
    assert report["summary"] == {
        "sources_checked": 2,
        "capture_metadata_sources": 1,
        "no_capture_sources": 0,
        "provider_errors": 0,
        "cumulative_sources": 2,
    }
    assert report["sources"][1]["wayback_status"] == "unsupported_url"


def test_wayback_shards_are_deterministic_and_reports_merge(monkeypatch):
    monkeypatch.setattr("scripts.triangulate_wayback.query_wayback", lambda url: [])
    matrix = {"sources": [{"source_id": f"source-{i}", "url": f"https://example.govt.nz/{i}"} for i in range(8)]}
    first = triangulate(matrix, limit=2, shard_index=0, shard_count=2, delay=0, retries=1)
    second = triangulate(matrix, limit=2, shard_index=0, shard_count=2, offset=2, delay=0, retries=1,
                         existing_report=first)
    assert first["batch"]["shard_count"] == 2
    assert second["batch"]["offset"] == 2
    assert second["summary"]["cumulative_sources"] == 4
    assert len(second["sources"]) == 4


def test_wayback_retries_transient_failures(monkeypatch):
    calls = {"count": 0}

    def query(url):
        calls["count"] += 1
        if calls["count"] < 3:
            raise TimeoutError("temporary")
        return []

    monkeypatch.setattr("scripts.triangulate_wayback.query_wayback", query)
    report = triangulate({"sources": [{"source_id": "x", "url": "https://example.govt.nz/"}]},
                         limit=1, delay=0, retries=3, backoff=0)
    assert calls["count"] == 3
    assert report["sources"][0]["wayback_status"] == "no_capture_found"


def test_wayback_workflow_exposes_batch_and_retry_controls():
    workflow = Path(".github/workflows/triangulate_wayback.yml").read_text(encoding="utf-8")
    for option in ("--offset", "--shard-index", "--shard-count", "--retries", "--backoff"):
        assert option in workflow
