import argparse
import json
from urllib.error import HTTPError

import scripts.archive_registered_sources as archive_registered_sources
from scripts.archive_registered_sources import (
    archive_bluesky_source,
    archive_manual_seed_source,
    archive_rss_source,
    archive_website_source,
    archive_youtube_source,
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


class FakeYouTubeFeed:
    entries = [
        {
            "title": "Video update",
            "summary": "Public YouTube update",
            "link": "https://www.youtube.com/watch?v=abc123",
            "published": "Wed, 24 Jun 2026 01:00:00 GMT",
            "yt_videoid": "abc123",
        }
    ]


class FakeYouTubeParser:
    def parse(self, url):
        self.url = url
        return FakeYouTubeFeed()

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
                    {
                        "source_id": "agency-youtube",
                        "agency_id": "agency",
                        "platform": "youtube",
                        "source_type": "social_profile",
                        "url": "https://www.youtube.com/@agency",
                        "archive_status": "candidate",
                        "feasibility": "medium",
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

    assert report["summary"]["selected_sources"] == 4
    assert report["summary"]["status_counts"] == {
        "manual_seed_missing": 1,
        "would_capture": 3,
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



def test_archive_bluesky_source_rejects_intent_share_url(tmp_path):
    source = {
        "source_id": "agency-bluesky-share",
        "agency_id": "agency",
        "platform": "bluesky",
        "source_type": "social_profile",
        "url": "https://bsky.app/intent/compose?text=Home&url=https%3A%2F%2Fagency.govt.nz",
        "archive_status": "ready",
        "feasibility": "high",
    }

    results = archive_bluesky_source(
        source,
        raw_root=tmp_path / "raw",
        normalized_root=tmp_path / "normalized",
        fetcher=lambda actor, handle, max_pages: [],
    )

    assert results[0]["status"] == "capture_failed"
    assert results[0]["reason"] == "missing Bluesky handle"




def test_archive_youtube_source_resolves_channel_and_writes_records(tmp_path):
    source = {
        "source_id": "agency-youtube",
        "agency_id": "agency",
        "platform": "youtube",
        "source_type": "social_profile",
        "url": "https://www.youtube.com/@agency",
        "account": "Agency YouTube",
        "archive_status": "candidate",
        "feasibility": "medium",
    }
    parser = FakeYouTubeParser()

    results = archive_youtube_source(
        source,
        raw_root=tmp_path / "raw",
        normalized_root=tmp_path / "normalized",
        parser=parser,
        page_fetcher=lambda url: '{"channelId":"UC1234567890abcdefghiJKL"}',
    )

    assert results[0]["status"] == "captured"
    assert parser.url == "https://www.youtube.com/feeds/videos.xml?channel_id=UC1234567890abcdefghiJKL"
    assert list((tmp_path / "raw" / "youtube" / "2026-06").glob("*.json"))
    normalized = (tmp_path / "normalized" / "youtube" / "2026-06.jsonl").read_text(encoding="utf-8")
    assert "youtube:" in normalized
    assert "Public YouTube update" in normalized
    assert "UC1234567890abcdefghiJKL" in normalized


def test_archive_youtube_source_reports_unresolved_channel(tmp_path):
    source = {
        "source_id": "agency-youtube",
        "agency_id": "agency",
        "platform": "youtube",
        "source_type": "social_profile",
        "url": "https://www.youtube.com/@agency",
        "archive_status": "candidate",
        "feasibility": "medium",
    }

    results = archive_youtube_source(
        source,
        raw_root=tmp_path / "raw",
        normalized_root=tmp_path / "normalized",
        parser=FakeYouTubeParser(),
        page_fetcher=lambda url: "<html>No channel id</html>",
    )

    assert results == [
        {
            "source_id": "agency-youtube",
            "agency_id": "agency",
            "platform": "youtube",
            "source_type": "social_profile",
            "url": "https://www.youtube.com/@agency",
            "archive_status": "candidate",
            "feasibility": "medium",
            "status": "capture_failed",
            "reason": "could not resolve YouTube channel id",
        }
    ]

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


def threads_source() -> dict[str, str]:
    return {
        "source_id": "agency-threads",
        "agency_id": "agency",
        "platform": "threads",
        "source_type": "social_profile",
        "url": "https://www.threads.net/@agency",
        "account": "agency",
        "archive_status": "ready",
        "feasibility": "medium",
    }


def report_args(tmp_path, manifest, *, dry_run=False):
    return argparse.Namespace(
        manifest=manifest,
        report=tmp_path / "report.json",
        source_type="threads",
        agency_id="",
        include_blocked=True,
        dry_run=dry_run,
        raw_root=tmp_path / "raw",
        normalized_root=tmp_path / "normalized",
        manual_seed_root=tmp_path / "manual_archive_seeds",
        max_threads_posts=25,
    )


def write_threads_manifest(tmp_path, source=None):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"sources": [source or threads_source()]}), encoding="utf-8")
    return manifest


def test_archive_threads_api_disabled_reports_missing_seed(tmp_path, monkeypatch):
    monkeypatch.delenv("THREADS_API_CAPTURE_ENABLED", raising=False)
    manifest = write_threads_manifest(tmp_path)

    report = build_report(report_args(tmp_path, manifest))

    assert report["summary"]["status_counts"] == {"manual_seed_missing": 1}
    result = report["results"][0]
    assert result["status"] == "manual_seed_missing"
    assert "live API capture is disabled" in result["reason"]


def test_archive_threads_api_disabled_archives_authorized_seed(tmp_path, monkeypatch):
    monkeypatch.delenv("THREADS_API_CAPTURE_ENABLED", raising=False)
    manifest = write_threads_manifest(tmp_path)
    seed_dir = tmp_path / "manual_archive_seeds" / "threads"
    seed_dir.mkdir(parents=True)
    (seed_dir / "agency-threads.json").write_text(
        json.dumps(
            {
                "posts": [
                    {
                        "post_id": "threads-seed-1",
                        "url": "https://www.threads.net/@agency/post/1",
                        "created_at": "2026-06-10T00:00:00Z",
                        "text": "Authorized Threads seed",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    report = build_report(report_args(tmp_path, manifest))

    assert report["summary"]["status_counts"] == {"manual_seed_captured": 1}
    normalized_path = tmp_path / "normalized" / "threads" / "2026-06.jsonl"
    record = json.loads(normalized_path.read_text(encoding="utf-8"))
    assert record["source_platform"] == "threads"
    assert record["content"] == "Authorized Threads seed"


def test_archive_threads_api_enabled_reports_permission_error(tmp_path, monkeypatch):
    monkeypatch.setenv("THREADS_API_CAPTURE_ENABLED", "true")
    monkeypatch.setenv("THREADS_ACCESS_TOKEN", "token")
    manifest = write_threads_manifest(tmp_path)

    def blocked_urlopen(request, timeout=30):
        raise HTTPError(
            request.full_url,
            400,
            "Bad Request",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr(archive_registered_sources, "urlopen", blocked_urlopen)

    report = build_report(report_args(tmp_path, manifest))

    assert report["summary"]["status_counts"] == {"threads_permission_error": 1}
    assert report["results"][0]["status"] == "threads_permission_error"


def test_archive_threads_api_disabled_never_reports_api_blocker_status(tmp_path, monkeypatch):
    monkeypatch.delenv("THREADS_API_CAPTURE_ENABLED", raising=False)
    monkeypatch.setenv("THREADS_ACCESS_TOKEN", "token")
    manifest = write_threads_manifest(tmp_path)

    def unexpected_urlopen(request, timeout=30):
        raise AssertionError("Threads API should not be called when capture is disabled")

    monkeypatch.setattr(archive_registered_sources, "urlopen", unexpected_urlopen)

    report = build_report(report_args(tmp_path, manifest))

    assert report["summary"]["status_counts"] == {"manual_seed_missing": 1}
    assert report["results"][0]["status"] not in {"threads_permission_error", "threads_api_error"}


