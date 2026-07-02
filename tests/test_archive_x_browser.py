import argparse
import json
from pathlib import Path

from scripts.archive_x_browser import (
    archive_x_browser_sources,
    build_report,
    dedupe_x_sources,
    extract_posts_from_html,
    normalize_x_handle,
)


def test_normalize_x_handle_supports_x_and_twitter_urls():
    assert normalize_x_handle({"url": "https://x.com/AntarcticaNZ"}) == "AntarcticaNZ"
    assert normalize_x_handle({"url": "https://twitter.com/AntarcticaNZ"}) == "AntarcticaNZ"
    assert normalize_x_handle({"account": "twitter.com/AntarcticaNZ"}) == "AntarcticaNZ"


def test_dedupe_x_sources_prefers_ready_source():
    sources = [
        {
            "source_id": "old",
            "agency_id": "agency",
            "platform": "x",
            "source_type": "social_profile",
            "url": "https://twitter.com/Agency",
            "archive_status": "degraded",
        },
        {
            "source_id": "new",
            "agency_id": "agency",
            "platform": "x",
            "source_type": "social_profile",
            "url": "https://x.com/Agency",
            "account": "Agency",
            "archive_status": "ready",
        },
    ]

    deduped = dedupe_x_sources(sources)

    assert len(deduped) == 1
    assert deduped[0]["source_id"] == "new"
    assert deduped[0]["duplicate_source_ids"] == ["old", "new"]


def test_extract_posts_from_html_finds_status_urls():
    html = Path("tests/fixtures/x_timeline_sample.html").read_text(encoding="utf-8")

    posts = extract_posts_from_html(html, handle="agency")

    assert [post["tweet_id"] for post in posts] == ["1111111111111111111", "2222222222222222222"]


def test_extract_posts_from_html_includes_empty_card_metadata() -> None:
    posts = extract_posts_from_html('<a href="https://x.com/agency/status/3333333333333333333">post</a>', handle="agency")

    assert posts[0]["external_links"] == []
    assert posts[0]["card_links"] == []
    assert posts[0]["media"] == []


def test_archive_x_browser_sources_fixture_writes_raw_normalized_and_report(tmp_path):
    html = Path("tests/fixtures/x_timeline_sample.html").read_text(encoding="utf-8")
    source = {
        "source_id": "agency-x",
        "agency_id": "agency",
        "platform": "x",
        "source_type": "social_profile",
        "url": "https://x.com/agency",
        "account": "agency",
        "archive_status": "ready",
        "feasibility": "low",
    }

    results = archive_x_browser_sources(
        [source],
        raw_root=tmp_path / "raw",
        normalized_root=tmp_path / "normalized",
        fixture_html=html,
    )

    assert results[0]["status"] == "browser_posts_captured"
    assert list((tmp_path / "raw" / "x_browser").glob("*/*.json"))
    normalized = (tmp_path / "normalized" / "x" / "2026-07.jsonl").read_text(encoding="utf-8")
    records = [json.loads(line) for line in normalized.splitlines()]
    assert {record["record_id"] for record in records} == {
        "x_browser:1111111111111111111",
        "x_browser:2222222222222222222",
    }


def test_build_report_fixture_counts_deduped_sources(tmp_path):
    manifest = tmp_path / "manifest.json"
    fixture = Path("tests/fixtures/x_timeline_sample.html")
    manifest.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "source_id": "agency-x-old",
                        "agency_id": "agency",
                        "platform": "x",
                        "source_type": "social_profile",
                        "url": "https://twitter.com/agency",
                        "archive_status": "degraded",
                    },
                    {
                        "source_id": "agency-x-new",
                        "agency_id": "agency",
                        "platform": "x",
                        "source_type": "social_profile",
                        "url": "https://x.com/agency",
                        "archive_status": "ready",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    report = build_report(
        argparse.Namespace(
            manifest=manifest,
            report=tmp_path / "report.json",
            raw_root=tmp_path / "raw",
            normalized_root=tmp_path / "normalized",
            agency_id="",
            dry_run=False,
            offset_sources=0,
            limit_sources=0,
            max_scrolls=1,
            idle_rounds=1,
            per_account_timeout=10,
            fixture_html=str(fixture),
        )
    )

    assert report["summary"]["manifest_x_source_count"] == 2
    assert report["summary"]["selected_sources"] == 1
    assert report["summary"]["status_counts"] == {"browser_posts_captured": 1}
