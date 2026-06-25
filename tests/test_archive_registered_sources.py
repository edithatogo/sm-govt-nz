import argparse
import json

from scripts.archive_registered_sources import (
    archive_bluesky_source,
    archive_manual_seed_source,
    archive_rss_source,
    archive_website_source,
    build_report,
)


class FakeFeed:
    entries = [
        {
            "title": "Update",
            "summary": "Published update",
            "link": "https://agency.example/news/update",
            "published": "Wed, 24 Jun 2026 01:00:00 GMT",
        }
    ]


class FakeParser:
    def parse(self, url):
        self.url = url
        return FakeFeed()


def test_archive_registered_sources_reports_supported_and_pending_sources(tmp_path):
    manifest = tmp_path / "manifest.json"
    report_path = tmp_path / "report.json"
    manifest.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "source_id": "courts-nz-bluesky",
                        "agency_id": "courts-nz",
                        "platform": "bluesky",
                        "source_type": "social_profile",
                        "url": "https://bsky.app/profile/courtsofnz.bsky.social",
                        "archive_status": "ready",
                        "feasibility": "high",
                    },
                    {
                        "source_id": "agency-rss",
                        "agency_id": "agency",
                        "platform": "rss",
                        "source_type": "rss_feed",
                        "url": "https://agency.example/rss",
                        "archive_status": "ready",
                        "feasibility": "high",
                    },
                    {
                        "source_id": "agency-linkedin",
                        "agency_id": "agency",
                        "platform": "linkedin",
                        "source_type": "social_profile",
                        "url": "https://linkedin.example/company/agency",
                        "archive_status": "manual_seed",
                        "feasibility": "low",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    report = build_report(
        argparse.Namespace(
            manifest=manifest,
            report=report_path,
            source_type="all_feasible",
            agency_id="",
            include_blocked=True,
            dry_run=True,
            raw_root=tmp_path / "raw",
            normalized_root=tmp_path / "normalized",
        )
    )

    assert report["summary"]["selected_sources"] == 3
    assert report["summary"]["status_counts"] == {
        "manual_seed_missing": 1,
        "would_capture": 2,
    }
    assert report["courts_current_sources_report"] == {
        "dry_run": True,
        "selected_supported_courts_sources": 1,
    }


def test_archive_rss_source_writes_raw_and_normalized_records(tmp_path):
    source = {
        "source_id": "agency-rss",
        "agency_id": "agency",
        "platform": "rss",
        "source_type": "rss_feed",
        "url": "https://agency.example/rss",
        "account": "Agency RSS",
        "archive_status": "ready",
        "feasibility": "high",
    }

    results = archive_rss_source(
        source,
        raw_root=tmp_path / "raw",
        normalized_root=tmp_path / "normalized",
        parser=FakeParser(),
    )

    assert results[0]["status"] == "captured"
    raw_files = list((tmp_path / "raw" / "rss" / "2026-06").glob("*.json"))
    assert raw_files
    normalized = (tmp_path / "normalized" / "rss" / "2026-06.jsonl").read_text(encoding="utf-8")
    assert "rss:" in normalized
    assert "Published update" in normalized


def test_archive_website_source_writes_raw_and_normalized_records(tmp_path):
    source = {
        "source_id": "agency-website",
        "agency_id": "agency",
        "platform": "website_page",
        "source_type": "website_page",
        "url": "https://agency.example",
        "account": "Agency",
        "archive_status": "ready",
        "feasibility": "high",
    }

    result = archive_website_source(
        source,
        raw_root=tmp_path / "raw",
        normalized_root=tmp_path / "normalized",
        website_fetcher=lambda url: "<html><title>Agency</title><body>Public update</body></html>",
    )

    assert result["status"] == "captured"
    assert list((tmp_path / "raw" / "website" / "2026-06").glob("*.json"))
    normalized = (tmp_path / "normalized" / "website" / "2026-06.jsonl").read_text(encoding="utf-8")
    assert "website:" in normalized
    assert "Public update" in normalized



def test_archive_bluesky_source_writes_raw_and_normalized_records(tmp_path):
    source = {
        "source_id": "agency-bluesky",
        "agency_id": "agency",
        "platform": "bluesky",
        "source_type": "social_profile",
        "url": "https://bsky.app/profile/agency.bsky.social",
        "account": "agency.bsky.social",
        "archive_status": "ready",
        "feasibility": "high",
    }

    results = archive_bluesky_source(
        source,
        raw_root=tmp_path / "raw",
        normalized_root=tmp_path / "normalized",
        fetcher=lambda actor, handle, max_pages: [
            {
                "post_id": "abc123",
                "uri": "at://did/post/abc123",
                "cid": "cid123",
                "text": "Public Bluesky update",
                "created_at": "2026-06-24T01:00:00+00:00",
                "url": "https://bsky.app/profile/agency.bsky.social/post/abc123",
                "images": [],
            }
        ],
    )

    assert results[0]["status"] == "captured"
    assert (tmp_path / "raw" / "bluesky" / "2026-06" / "abc123.json").is_file()
    normalized = (tmp_path / "normalized" / "bluesky" / "2026-06.jsonl").read_text(encoding="utf-8")
    assert "bluesky:abc123" in normalized
    assert "Public Bluesky update" in normalized


def test_archive_rss_source_does_not_rewrite_existing_raw_record(tmp_path):
    source = {
        "source_id": "agency-rss",
        "agency_id": "agency",
        "platform": "rss",
        "source_type": "rss_feed",
        "url": "https://agency.example/rss",
        "account": "Agency RSS",
        "archive_status": "ready",
        "feasibility": "high",
    }
    raw_root = tmp_path / "raw"
    normalized_root = tmp_path / "normalized"

    archive_rss_source(source, raw_root=raw_root, normalized_root=normalized_root, parser=FakeParser())
    raw_file = next((raw_root / "rss" / "2026-06").glob("*.json"))
    original_raw = raw_file.read_text(encoding="utf-8")

    results = archive_rss_source(source, raw_root=raw_root, normalized_root=normalized_root, parser=FakeParser())

    assert results[0]["status"] == "already_captured"
    assert raw_file.read_text(encoding="utf-8") == original_raw


def test_archive_website_source_does_not_rewrite_existing_raw_record(tmp_path):
    source = {
        "source_id": "agency-website",
        "agency_id": "agency",
        "platform": "website_page",
        "source_type": "website_page",
        "url": "https://agency.example",
        "account": "Agency",
        "archive_status": "ready",
        "feasibility": "high",
    }
    raw_root = tmp_path / "raw"
    normalized_root = tmp_path / "normalized"

    archive_website_source(
        source,
        raw_root=raw_root,
        normalized_root=normalized_root,
        website_fetcher=lambda url: "<html>original</html>",
    )
    raw_file = next((raw_root / "website").glob("*/*.json"))
    original_raw = raw_file.read_text(encoding="utf-8")

    result = archive_website_source(
        source,
        raw_root=raw_root,
        normalized_root=normalized_root,
        website_fetcher=lambda url: "<html>changed</html>",
    )

    assert result["status"] == "already_captured"
    assert raw_file.read_text(encoding="utf-8") == original_raw


def test_archive_bluesky_source_does_not_rewrite_existing_raw_record(tmp_path):
    source = {
        "source_id": "agency-bluesky",
        "agency_id": "agency",
        "platform": "bluesky",
        "source_type": "social_profile",
        "url": "https://bsky.app/profile/agency.bsky.social",
        "account": "agency.bsky.social",
        "archive_status": "ready",
        "feasibility": "high",
    }
    raw_root = tmp_path / "raw"
    normalized_root = tmp_path / "normalized"
    posts = [
        {
            "post_id": "abc123",
            "uri": "at://did/post/abc123",
            "cid": "cid123",
            "text": "Public Bluesky update",
            "created_at": "2026-06-24T01:00:00+00:00",
            "url": "https://bsky.app/profile/agency.bsky.social/post/abc123",
            "images": [],
        }
    ]

    archive_bluesky_source(
        source,
        raw_root=raw_root,
        normalized_root=normalized_root,
        fetcher=lambda actor, handle, max_pages: posts,
    )
    raw_file = raw_root / "bluesky" / "2026-06" / "abc123.json"
    original_raw = raw_file.read_text(encoding="utf-8")
    posts[0]["text"] = "Changed text"

    results = archive_bluesky_source(
        source,
        raw_root=raw_root,
        normalized_root=normalized_root,
        fetcher=lambda actor, handle, max_pages: posts,
    )

    assert results[0]["status"] == "already_captured"
    assert raw_file.read_text(encoding="utf-8") == original_raw


def test_archive_manual_seed_reports_missing_seed(tmp_path):
    source = {
        "source_id": "agency-linkedin",
        "agency_id": "agency",
        "platform": "linkedin",
        "source_type": "social_profile",
        "url": "https://www.linkedin.com/company/agency",
        "account": "Agency",
        "archive_status": "manual_seed",
        "feasibility": "medium",
    }

    results = archive_manual_seed_source(
        source,
        raw_root=tmp_path / "raw",
        normalized_root=tmp_path / "normalized",
        manual_seed_root=tmp_path / "manual_archive_seeds",
    )

    assert results == [
        {
            "source_id": "agency-linkedin",
            "agency_id": "agency",
            "platform": "linkedin",
            "source_type": "social_profile",
            "url": "https://www.linkedin.com/company/agency",
            "archive_status": "manual_seed",
            "feasibility": "medium",
            "status": "manual_seed_missing",
            "reason": "linkedin capture requires an operator-authorized seed JSON under manual_archive_seeds/linkedin/",
        }
    ]


def test_archive_manual_seed_writes_registered_source_records(tmp_path):
    source = {
        "source_id": "agency-linkedin",
        "agency_id": "agency",
        "platform": "linkedin",
        "source_type": "social_profile",
        "url": "https://www.linkedin.com/company/agency",
        "account": "Agency",
        "archive_status": "manual_seed",
        "feasibility": "medium",
    }
    seed_dir = tmp_path / "manual_archive_seeds" / "linkedin"
    seed_dir.mkdir(parents=True)
    (seed_dir / "agency-linkedin.json").write_text(
        json.dumps(
            {
                "posts": [
                    {
                        "post_id": "urn:li:activity:registered",
                        "url": "https://www.linkedin.com/feed/update/urn:li:activity:registered/",
                        "created_at": "2026-06-10T00:00:00Z",
                        "text": "Registered LinkedIn update",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    results = archive_manual_seed_source(
        source,
        raw_root=tmp_path / "raw",
        normalized_root=tmp_path / "normalized",
        manual_seed_root=tmp_path / "manual_archive_seeds",
    )

    assert results[0]["status"] == "manual_seed_captured"
    raw_path = tmp_path / "raw" / "linkedin" / "2026-06" / "urnliactivityregistered.json"
    normalized_path = tmp_path / "normalized" / "linkedin" / "2026-06.jsonl"
    record = json.loads(normalized_path.read_text(encoding="utf-8"))
    assert raw_path.exists()
    assert record["agency_id"] == "agency"
    assert record["source_account"] == "Agency"
    assert record["source_kind"] == "social_profile"
    assert record["cross_source_ids"]["source_id"] == "agency-linkedin"


def test_archive_registered_sources_dry_run_reports_missing_linkedin_seed(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "source_id": "agency-linkedin",
                        "agency_id": "agency",
                        "platform": "linkedin",
                        "source_type": "social_profile",
                        "url": "https://www.linkedin.com/company/agency",
                        "archive_status": "manual_seed",
                        "feasibility": "medium",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    report = build_report(
        argparse.Namespace(
            manifest=manifest,
            report=tmp_path / "report.json",
            source_type="linkedin",
            agency_id="",
            include_blocked=True,
            dry_run=True,
            raw_root=tmp_path / "raw",
            normalized_root=tmp_path / "normalized",
            manual_seed_root=tmp_path / "manual_archive_seeds",
        )
    )

    assert report["summary"]["status_counts"] == {"manual_seed_missing": 1}
    assert report["summary"]["status_by_platform"] == {"linkedin": {"manual_seed_missing": 1}}


