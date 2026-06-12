import json

from src.rss_discovery import discover_rss_feeds, write_rss_discovery_report


def test_discover_rss_feeds_from_link_rel_and_anchor(tmp_path):
    pages = {
        "https://example.test/news": """
            <html>
              <head>
                <link rel="alternate" type="application/rss+xml" title="News RSS" href="/news/rss.xml">
                <link rel="alternate stylesheet" type="text/css" href="/theme.css">
              </head>
              <body>
                <a href="/announcements/atom.xml" title="Announcements Atom">Feed</a>
              </body>
            </html>
        """,
        "https://example.test/cases": """
            <html>
              <head>
                <link rel="alternate" type="application/rss+xml" title="News RSS" href="/news/rss.xml#fragment">
              </head>
            </html>
        """,
    }

    report = discover_rss_feeds(
        agency_id="courts-nz",
        seed_pages=list(pages),
        fetcher=pages.__getitem__,
        generated_at="2026-06-12T00:00:00+00:00",
    )

    assert report.feed_count == 2
    assert [feed.feed_url for feed in report.feeds] == [
        "https://example.test/announcements/atom.xml",
        "https://example.test/news/rss.xml",
    ]
    assert {page.status for page in report.seed_pages} == {"healthy"}


def test_discover_rss_feeds_records_unavailable_seed_page():
    def fetcher(url: str) -> str:
        if url.endswith("/missing"):
            raise RuntimeError("not found")
        return '<link rel="alternate" type="application/rss+xml" href="/feed.xml">'

    report = discover_rss_feeds(
        agency_id="courts-nz",
        seed_pages=["https://example.test/ok", "https://example.test/missing"],
        fetcher=fetcher,
        generated_at="2026-06-12T00:00:00+00:00",
    )

    assert report.feed_count == 1
    assert report.seed_pages[1].status == "unavailable"
    assert report.seed_pages[1].error == "not found"


def test_write_rss_discovery_report(tmp_path):
    report = discover_rss_feeds(
        agency_id="courts-nz",
        seed_pages=["https://example.test/ok"],
        fetcher=lambda _url: '<link rel="alternate" type="application/rss+xml" href="/feed.xml">',
        generated_at="2026-06-12T00:00:00+00:00",
    )
    output_path = tmp_path / "feeds.json"

    write_rss_discovery_report(report, output_path)

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["agency_id"] == "courts-nz"
    assert payload["feeds"][0]["feed_url"] == "https://example.test/feed.xml"
