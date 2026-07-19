import json
from pathlib import Path
from urllib.error import HTTPError

from scripts.triangulate_common_crawl import latest_index, query_index, triangulate


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.payload


def test_common_crawl_index_parsers():
    def opener(request, timeout):
        if "collinfo" in request.full_url:
            return FakeResponse(json.dumps([{"cdx-api": "https://index.commoncrawl.org/CC-MAIN-test-index"}]).encode())
        return FakeResponse(b'{"timestamp":"20250101000000","url":"https://example.govt.nz/"}\n')

    assert latest_index(opener=opener) == "https://index.commoncrawl.org/CC-MAIN-test-index"
    assert query_index("https://index.commoncrawl.org/CC-MAIN-test-index", "https://example.govt.nz/", opener=opener)[0]["url"] == "https://example.govt.nz/"


def test_common_crawl_triangulation_does_not_download_snapshots(monkeypatch):
    monkeypatch.setattr("scripts.triangulate_common_crawl.latest_index", lambda: "https://index.test")
    monkeypatch.setattr("scripts.triangulate_common_crawl.query_index", lambda index, url: [])
    report = triangulate({"sources": [{"source_id": "x", "platform": "website_page", "url": "https://example.govt.nz/"}]}, limit=1, delay=0)
    assert report["snapshot_downloaded"] is False
    assert report["summary"]["no_capture_sources"] == 1
    assert report["summary"]["cumulative_sources"] == 1


def test_common_crawl_404_is_an_empty_result():
    def opener(request, timeout):
        raise HTTPError(request.full_url, 404, "not indexed", {}, None)

    assert query_index("https://index.test", "https://example.govt.nz/", opener=opener) == []


def test_common_crawl_shards_are_deterministic_and_reports_merge(monkeypatch):
    monkeypatch.setattr("scripts.triangulate_common_crawl.latest_index", lambda: "https://index.test")
    monkeypatch.setattr("scripts.triangulate_common_crawl.query_index", lambda index, url: [])
    matrix = {"sources": [{"source_id": f"source-{i}", "url": f"https://example.govt.nz/{i}"} for i in range(8)]}
    first = triangulate(matrix, limit=2, shard_index=1, shard_count=2, delay=0, retries=1)
    second = triangulate(matrix, limit=2, shard_index=1, shard_count=2, offset=2, delay=0, retries=1,
                         existing_report=first)
    assert first["batch"]["shard_count"] == 2
    assert second["batch"]["offset"] == 2
    assert second["summary"]["cumulative_sources"] == 4


def test_common_crawl_retries_transient_failures(monkeypatch):
    calls = {"count": 0}
    monkeypatch.setattr("scripts.triangulate_common_crawl.latest_index", lambda: "https://index.test")

    def query(index, url):
        calls["count"] += 1
        if calls["count"] < 3:
            raise TimeoutError("temporary")
        return []

    monkeypatch.setattr("scripts.triangulate_common_crawl.query_index", query)
    report = triangulate({"sources": [{"source_id": "x", "url": "https://example.govt.nz/"}]},
                         limit=1, delay=0, retries=3, backoff=0)
    assert calls["count"] == 3
    assert report["sources"][0]["common_crawl_status"] == "no_capture_found"


def test_common_crawl_workflow_exposes_batch_and_retry_controls():
    workflow = Path(".github/workflows/triangulate_common_crawl.yml").read_text(encoding="utf-8")
    for option in ("--offset", "--shard-index", "--shard-count", "--retries", "--backoff"):
        assert option in workflow
