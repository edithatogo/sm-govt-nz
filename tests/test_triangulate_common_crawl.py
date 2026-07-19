import json
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


def test_common_crawl_404_is_an_empty_result():
    def opener(request, timeout):
        raise HTTPError(request.full_url, 404, "not indexed", {}, None)

    assert query_index("https://index.test", "https://example.govt.nz/", opener=opener) == []
