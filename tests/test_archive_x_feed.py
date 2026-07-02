import argparse
import json
from pathlib import Path

from scripts.archive_x_feed import (
    archive_x_feed_sources,
    base_urls_from_value,
    build_feed_urls,
    build_report,
    providers_from_value,
)


def test_provider_and_base_url_parsing_is_deterministic():
    assert providers_from_value("rsshub,nitter,twscrape,twscrape,unknown") == ["rsshub", "nitter", "twscrape"]
    assert base_urls_from_value("https://one.example/, https://two.example", ["https://fallback"]) == [
        "https://one.example",
        "https://two.example",
    ]
    assert build_feed_urls(
        "rsshub",
        "Agency_NZ",
        rsshub_base_urls=["https://rsshub.example"],
        nitter_base_urls=["https://xcancel.com"],
    ) == ["https://rsshub.example/twitter/user/Agency_NZ"]
    assert build_feed_urls(
        "nitter",
        "Agency_NZ",
        rsshub_base_urls=["https://rsshub.example"],
        nitter_base_urls=["https://xcancel.com"],
    ) == ["https://xcancel.com/Agency_NZ/rss"]


def test_archive_x_feed_sources_writes_raw_and_normalized_records(tmp_path):
    rsshub = Path("tests/fixtures/x_rsshub_feed.xml").read_text(encoding="utf-8")
    nitter = Path("tests/fixtures/x_nitter_feed.xml").read_text(encoding="utf-8")
    source = {
        "source_id": "agency-x",
        "agency_id": "agency",
        "platform": "x",
        "source_type": "social_profile",
        "url": "https://x.com/agency",
        "account": "agency",
        "archive_status": "ready",
    }

    def fetcher(url: str, timeout: int = 30) -> str:
        if "rsshub.example" in url:
            return rsshub
        if "xcancel.example" in url:
            return nitter
        raise AssertionError(url)

    results = archive_x_feed_sources(
        [source],
        raw_root=tmp_path / "raw",
        normalized_root=tmp_path / "normalized",
        providers="rsshub,nitter",
        rsshub_base_urls="https://rsshub.example",
        nitter_base_urls="https://xcancel.example",
        fetcher=fetcher,
    )

    assert [result["status"] for result in results] == ["feed_captured", "feed_captured"]
    assert list((tmp_path / "raw" / "x_feed").glob("*/*.json"))
    normalized = (tmp_path / "normalized" / "x" / "2026-07.jsonl").read_text(encoding="utf-8")
    records = [json.loads(line) for line in normalized.splitlines()]
    assert {record["record_id"] for record in records} == {
        "x_feed:1111111111111111111",
        "x_feed:2222222222222222222",
    }
    assert {record["extraction_method"] for record in records} == {"x_rsshub_feed", "x_nitter_feed"}


def test_archive_x_feed_sources_dedupes_cross_provider_tweet_ids(tmp_path):
    rsshub = Path("tests/fixtures/x_rsshub_feed.xml").read_text(encoding="utf-8")
    source = {
        "source_id": "agency-x",
        "agency_id": "agency",
        "platform": "x",
        "source_type": "social_profile",
        "url": "https://twitter.com/agency",
        "archive_status": "ready",
    }

    results = archive_x_feed_sources(
        [source],
        raw_root=tmp_path / "raw",
        normalized_root=tmp_path / "normalized",
        providers="rsshub,nitter",
        rsshub_base_urls="https://rsshub.example",
        nitter_base_urls="https://xcancel.example",
        fetcher=lambda _url, timeout=30: rsshub,
    )

    assert [result["status"] for result in results] == ["feed_captured", "feed_already_captured"]
    normalized = (tmp_path / "normalized" / "x" / "2026-07.jsonl").read_text(encoding="utf-8")
    assert len(normalized.splitlines()) == 1


def test_auth_scraper_providers_are_disabled_by_default(tmp_path):
    source = {
        "source_id": "agency-x",
        "agency_id": "agency",
        "platform": "x",
        "source_type": "social_profile",
        "url": "https://x.com/agency",
        "archive_status": "ready",
    }

    results = archive_x_feed_sources(
        [source],
        raw_root=tmp_path / "raw",
        normalized_root=tmp_path / "normalized",
        providers="twscrape,scweet",
    )

    assert [result["status"] for result in results] == ["auth_scrape_disabled", "auth_scrape_disabled"]


def test_build_report_fixture_counts_provider_statuses(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "source_id": "agency-x",
                        "agency_id": "agency",
                        "platform": "x",
                        "source_type": "social_profile",
                        "url": "https://x.com/agency",
                        "archive_status": "ready",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    report = build_report(
        argparse.Namespace(
            manifest=manifest,
            raw_root=tmp_path / "raw",
            normalized_root=tmp_path / "normalized",
            agency_id="",
            dry_run=True,
            offset_sources=0,
            limit_sources=0,
            x_feed_providers="rsshub,nitter",
            rsshub_base_urls="https://rsshub.example",
            nitter_base_urls="https://xcancel.example",
            x_feed_timeout=30,
            x_feed_max_items=25,
            x_auth_scrape_enabled=False,
        )
    )

    assert report["summary"]["selected_sources"] == 1
    assert report["summary"]["status_counts"] == {"would_capture": 1}
    assert report["summary"]["status_by_provider"] == {"none": {"would_capture": 1}}
