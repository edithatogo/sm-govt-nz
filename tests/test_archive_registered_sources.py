import argparse
import json
import socket
from urllib.error import HTTPError, URLError

import scripts.archive_registered_sources as archive_registered_sources
from scripts.archive_registered_sources import (
    archive_api_source,
    archive_bluesky_source,
    archive_public_profile_snapshot_source,
    archive_json_feed_source,
    archive_manual_seed_source,
    archive_rss_source,
    archive_website_source,
    archive_x_public_snapshot_source,
    archive_x_source,
    archive_youtube_source,
    build_report,
    fetch_website_with_alternates,
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


def test_archive_medium_feed_source_uses_rss_path(tmp_path):
    source = {
        "source_id": "digital-council-medium-feed",
        "agency_id": "digital-council-aotearoa-new-zealand",
        "platform": "rss",
        "source_type": "rss_feed",
        "url": "https://medium.com/feed/@digitalcouncilnz",
        "account": "Digital Council for Aotearoa New Zealand",
        "archive_status": "candidate",
        "feasibility": "medium",
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
    assert "medium.com/feed/@digitalcouncilnz" in normalized
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
    assert list((tmp_path / "raw" / "website").glob("*/*.json"))
    normalized_files = list((tmp_path / "normalized" / "website").glob("*.jsonl"))
    assert normalized_files
    normalized = normalized_files[0].read_text(encoding="utf-8")
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
            "status": "youtube_channel_unresolved",
            "reason": "could not resolve YouTube channel id",
        }
    ]


def test_archive_youtube_source_reports_bad_non_youtube_url(tmp_path):
    source = {
        "source_id": "agency-youtube",
        "agency_id": "agency",
        "platform": "youtube",
        "source_type": "social_profile",
        "url": "https://agency.example/videos",
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

    assert results[0]["status"] == "source_url_not_channel"
    assert results[0]["reason"] == "YouTube channel resolver failed: not a YouTube URL"


def test_archive_youtube_source_reports_bad_youtube_non_channel_url(tmp_path):
    source = {
        "source_id": "agency-youtube",
        "agency_id": "agency",
        "platform": "youtube",
        "source_type": "social_profile",
        "url": "https://www.youtube.com/watch?v=abc123",
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

    assert results[0]["status"] == "capture_failed"
    assert "YouTube video metadata fetch failed" in results[0]["reason"]


def test_archive_youtube_video_source_writes_oembed_metadata(tmp_path):
    source = {
        "source_id": "agency-youtube-video",
        "agency_id": "agency",
        "platform": "youtube",
        "source_type": "social_profile",
        "url": "https://youtu.be/abc123",
        "account": "Agency video",
        "archive_status": "candidate",
        "feasibility": "medium",
    }

    results = archive_registered_sources.archive_youtube_video_source(
        source,
        raw_root=tmp_path / "raw",
        normalized_root=tmp_path / "normalized",
        metadata_fetcher=lambda url: {"title": "Council meeting", "author_name": "Agency Channel"},
    )

    assert results[0]["status"] == "captured"
    raw_files = list((tmp_path / "raw" / "youtube").glob("*/*.json"))
    assert raw_files
    normalized = list((tmp_path / "normalized" / "youtube").glob("*.jsonl"))[0].read_text(encoding="utf-8")
    assert "Council meeting" in normalized
    assert "generic_registered_youtube_video_oembed" in normalized


def test_archive_youtube_source_normalizes_spaces_in_handle(tmp_path):
    seen = []

    def page_fetcher(url):
        seen.append(url)
        return '{"channelId":"UC1234567890abcdefghiJKL"}'

    source = {
        "source_id": "agency-youtube",
        "agency_id": "agency",
        "platform": "youtube",
        "source_type": "social_profile",
        "url": "https://www.youtube.com/@tewanangao raukawa",
        "archive_status": "candidate",
        "feasibility": "medium",
    }

    archive_youtube_source(
        source,
        raw_root=tmp_path / "raw",
        normalized_root=tmp_path / "normalized",
        parser=FakeYouTubeParser(),
        page_fetcher=page_fetcher,
    )

    assert seen == ["https://www.youtube.com/@tewanangaoraukawa"]


def test_archive_json_feed_source_archives_single_json_object(tmp_path, monkeypatch):
    source = {
        "source_id": "agency-json",
        "agency_id": "agency",
        "platform": "json_feed",
        "source_type": "json_feed",
        "url": "https://agency.example/wp-json/wp/v2/pages/1",
        "account": "Agency",
        "archive_status": "ready",
        "feasibility": "high",
    }

    monkeypatch.setattr(
        archive_registered_sources,
        "fetch_text",
        lambda url, timeout=30: json.dumps(
            {
                "id": 1,
                "link": "https://agency.example/page",
                "date": "2026-06-10T00:00:00",
                "title": {"rendered": "Agency page"},
                "content": {"rendered": "Public API-backed page body"},
            }
        ),
    )

    results = archive_json_feed_source(source, raw_root=tmp_path / "raw", normalized_root=tmp_path / "normalized")

    assert results[0]["status"] == "captured"
    normalized = (tmp_path / "normalized" / "json_feed" / "2026-06.jsonl").read_text(encoding="utf-8")
    assert "Agency page" in normalized
    assert "Public API-backed page body" in normalized


def test_archive_api_source_archives_keyless_public_snapshot(tmp_path, monkeypatch):
    source = {
        "source_id": "agency-api",
        "agency_id": "agency",
        "platform": "api",
        "source_type": "api_endpoint",
        "url": "https://agency.example/openapi.json",
        "account": "Agency API",
        "archive_status": "candidate",
        "access_method": "public_api_or_openapi",
        "auth": "none",
        "feasibility": "medium",
    }
    monkeypatch.setattr(archive_registered_sources, "fetch_text", lambda url, timeout=30: '{"openapi":"3.1.0"}')

    results = archive_api_source(source, raw_root=tmp_path / "raw", normalized_root=tmp_path / "normalized")

    assert results[0]["status"] == "captured"
    assert list((tmp_path / "raw" / "api" / "2026-07").glob("*.json"))
    normalized = (tmp_path / "normalized" / "api" / "2026-07.jsonl").read_text(encoding="utf-8")
    assert "api:" in normalized
    assert "generic_keyless_api_snapshot" in normalized


def test_archive_api_source_reports_auth_required_for_non_keyless_source(tmp_path):
    source = {
        "source_id": "agency-api",
        "agency_id": "agency",
        "platform": "api",
        "source_type": "api_endpoint",
        "url": "https://agency.example/private",
        "archive_status": "candidate",
        "auth": "api_key_required",
    }

    results = archive_api_source(source, raw_root=tmp_path / "raw", normalized_root=tmp_path / "normalized")

    assert results[0]["status"] == "auth_required"


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


def test_fetch_website_with_alternates_uses_www_after_403():
    seen = []

    def fetcher(url, timeout):
        seen.append(url)
        if url == "https://agency.example":
            raise HTTPError(url, 403, "Forbidden", hdrs=None, fp=None)
        return "<html>fallback</html>"

    fetched_url, html = fetch_website_with_alternates("https://agency.example", fetcher, 5, allow_alternates=True)

    assert fetched_url == "https://www.agency.example"
    assert html == "<html>fallback</html>"
    assert seen == ["https://agency.example", "https://www.agency.example"]


def test_fetch_website_with_alternates_uses_www_after_406():
    def fetcher(url, timeout):
        if url == "https://agency.example":
            raise HTTPError(url, 406, "Not Acceptable", hdrs=None, fp=None)
        return "<html>fallback</html>"

    fetched_url, html = fetch_website_with_alternates("https://agency.example", fetcher, 5, allow_alternates=True)

    assert fetched_url == "https://www.agency.example"
    assert html == "<html>fallback</html>"


def test_fetch_website_with_alternates_uses_www_after_405():
    def fetcher(url, timeout):
        if url == "https://agency.example":
            raise HTTPError(url, 405, "Method Not Allowed", hdrs=None, fp=None)
        return "<html>fallback</html>"

    fetched_url, html = fetch_website_with_alternates("https://agency.example", fetcher, 5, allow_alternates=True)

    assert fetched_url == "https://www.agency.example"
    assert html == "<html>fallback</html>"



def test_fetch_website_with_alternates_tries_http_www_combination_after_405():
    seen = []

    def fetcher(url, timeout):
        seen.append(url)
        if url != "http://www.agency.example":
            raise HTTPError(url, 405, "Method Not Allowed", hdrs=None, fp=None)
        return "<html>fallback</html>"

    fetched_url, html = fetch_website_with_alternates("https://agency.example", fetcher, 5, allow_alternates=True)

    assert fetched_url == "http://www.agency.example"
    assert html == "<html>fallback</html>"
    assert seen == [
        "https://agency.example",
        "https://www.agency.example",
        "http://agency.example",
        "http://www.agency.example",
    ]


def test_archive_youtube_source_reports_missing_handle_as_channel_not_found(tmp_path):
    source = {
        "source_id": "agency-youtube",
        "agency_id": "agency",
        "platform": "youtube",
        "source_type": "social_profile",
        "url": "https://www.youtube.com/@retired",
        "archive_status": "candidate",
        "feasibility": "medium",
    }

    results = archive_youtube_source(
        source,
        raw_root=tmp_path / "raw",
        normalized_root=tmp_path / "normalized",
        parser=FakeYouTubeParser(),
        page_fetcher=lambda url: (_ for _ in ()).throw(HTTPError(url, 404, "Not Found", hdrs=None, fp=None)),
    )

    assert results[0]["status"] == "youtube_channel_not_found"
    assert results[0]["reason"] == "YouTube channel resolver failed: HTTP 404: YouTube channel page not found"
def test_archive_website_source_reports_dns_failure(tmp_path):
    result = archive_website_source(
        {
            "source_id": "agency-website",
            "agency_id": "agency",
            "platform": "website_page",
            "source_type": "website_page",
            "url": "https://agency.example",
            "archive_status": "ready",
            "feasibility": "high",
        },
        raw_root=tmp_path / "raw",
        normalized_root=tmp_path / "normalized",
        website_fetcher=lambda url: (_ for _ in ()).throw(URLError("getaddrinfo failed")),
    )

    assert result["status"] == "dns_failed"


def test_archive_website_source_reports_network_timeout(tmp_path):
    result = archive_website_source(
        {
            "source_id": "agency-website",
            "agency_id": "agency",
            "platform": "website_page",
            "source_type": "website_page",
            "url": "https://agency.example",
            "archive_status": "ready",
            "feasibility": "high",
        },
        raw_root=tmp_path / "raw",
        normalized_root=tmp_path / "normalized",
        website_fetcher=lambda url: (_ for _ in ()).throw(URLError(socket.timeout("timed out"))),
    )

    assert result["status"] == "network_timeout"


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




def test_archive_manual_seed_reports_empty_seed(tmp_path):
    source = {
        "source_id": "agency-newsletter",
        "agency_id": "agency",
        "platform": "newsletter",
        "source_type": "email_subscription",
        "url": "mailto:newsletter@example.govt.nz",
        "account": "Agency Newsletter",
        "archive_status": "manual_seed",
        "feasibility": "medium",
    }
    seed_dir = tmp_path / "manual_archive_seeds" / "newsletter"
    seed_dir.mkdir(parents=True)
    (seed_dir / "agency-newsletter.json").write_text(json.dumps({"posts": []}), encoding="utf-8")

    results = archive_manual_seed_source(
        source,
        raw_root=tmp_path / "raw",
        normalized_root=tmp_path / "normalized",
        manual_seed_root=tmp_path / "manual_archive_seeds",
    )

    assert results[0]["status"] == "seed_empty"
    assert "manual seed contained no newsletter posts" in results[0]["reason"]


def test_archive_manual_seed_reports_invalid_seed(tmp_path):
    source = {
        "source_id": "agency-threads",
        "agency_id": "agency",
        "platform": "threads",
        "source_type": "social_profile",
        "url": "https://www.threads.net/@agency",
        "account": "agency",
        "archive_status": "manual_seed",
        "feasibility": "medium",
    }
    seed_dir = tmp_path / "manual_archive_seeds" / "threads"
    seed_dir.mkdir(parents=True)
    (seed_dir / "agency-threads.json").write_text(json.dumps({"posts": [{"text": "missing url and date"}]}), encoding="utf-8")

    results = archive_manual_seed_source(
        source,
        raw_root=tmp_path / "raw",
        normalized_root=tmp_path / "normalized",
        manual_seed_root=tmp_path / "manual_archive_seeds",
    )

    assert results[0]["status"] == "seed_invalid"
    assert "missing url" in results[0]["reason"]
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


def x_source() -> dict[str, str]:
    return {
        "source_id": "agency-x",
        "agency_id": "agency",
        "platform": "x",
        "source_type": "social_profile",
        "url": "https://x.com/agency",
        "account": "agency",
        "archive_status": "ready",
        "feasibility": "medium",
    }


def test_archive_x_source_writes_official_api_records(tmp_path):
    def api_fetcher(endpoint, params):
        if endpoint == "/users/by/username/agency":
            return {"data": {"id": "12345", "username": "agency", "name": "Agency"}}
        if endpoint == "/users/12345/tweets":
            assert params["max_results"] == "5"
            return {
                "data": [
                    {
                        "id": "98765",
                        "author_id": "12345",
                        "created_at": "2026-06-10T00:00:00Z",
                        "text": "Official X API update",
                    }
                ],
                "includes": {},
            }
        raise AssertionError(f"unexpected endpoint {endpoint}")

    results = archive_x_source(
        x_source(),
        raw_root=tmp_path / "raw",
        normalized_root=tmp_path / "normalized",
        api_fetcher=api_fetcher,
        max_posts=1,
    )

    assert results[0]["status"] == "captured"
    raw_path = tmp_path / "raw" / "x" / "2026-06" / "98765.json"
    normalized_path = tmp_path / "normalized" / "x" / "2026-06.jsonl"
    record = json.loads(normalized_path.read_text(encoding="utf-8"))
    assert raw_path.exists()
    assert record["record_id"] == "x:98765"
    assert record["source_platform"] == "x"
    assert record["source_account"] == "agency"
    assert record["canonical_url"] == "https://x.com/agency/status/98765"
    assert record["content"] == "Official X API update"
    assert record["extraction_method"] == "official_x_api_user_timeline"


def test_archive_x_api_enabled_missing_credentials_reports_auth_required(tmp_path):
    results = archive_x_source(
        x_source(),
        raw_root=tmp_path / "raw",
        normalized_root=tmp_path / "normalized",
    )

    assert results[0]["status"] == "x_auth_required"


def test_archive_x_api_disabled_uses_public_snapshot_when_no_seed(tmp_path, monkeypatch):
    monkeypatch.delenv("X_API_CAPTURE_ENABLED", raising=False)
    monkeypatch.setattr(
        archive_registered_sources,
        "fetch_text",
        lambda url, timeout=30: "<html><head><title>Agency / X</title><meta property='og:description' content='Official agency updates on X'></head></html>",
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"sources": [x_source()]}), encoding="utf-8")

    report = build_report(
        argparse.Namespace(
            manifest=manifest,
            report=tmp_path / "report.json",
            source_type="x",
            agency_id="",
            include_blocked=True,
            dry_run=False,
            raw_root=tmp_path / "raw",
            normalized_root=tmp_path / "normalized",
            manual_seed_root=tmp_path / "manual_archive_seeds",
            max_x_posts=25,
        )
    )

    assert report["summary"]["status_counts"] == {"public_snapshot_captured": 1}
    assert report["results"][0]["status"] == "public_snapshot_captured"
    assert list((tmp_path / "raw" / "x_public_snapshot" / "2026-07").glob("*.json"))


def test_archive_x_public_snapshot_source_writes_profile_snapshot(tmp_path):
    result = archive_x_public_snapshot_source(
        x_source(),
        raw_root=tmp_path / "raw",
        normalized_root=tmp_path / "normalized",
        fetcher=lambda url, timeout=30: (
            "<html><head><title>Agency / X</title>"
            '<meta property="og:description" content="Official agency updates on X">'
            "</head><body></body></html>"
        ),
    )

    assert result["status"] == "public_snapshot_captured"
    assert list((tmp_path / "raw" / "x_public_snapshot" / "2026-07").glob("*.json"))
    normalized_path = tmp_path / "normalized" / "x" / "2026-07.jsonl"
    record = json.loads(normalized_path.read_text(encoding="utf-8"))
    assert record["source_platform"] == "x"
    assert record["source_kind"] == "public_profile_snapshot"
    assert record["extraction_method"] == "x_public_web_snapshot"
    assert "Official agency updates on X" in record["content"]


def test_archive_x_api_disabled_uses_public_snapshot_fallback_when_enabled(tmp_path, monkeypatch):
    monkeypatch.delenv("X_API_CAPTURE_ENABLED", raising=False)
    monkeypatch.setattr(
        archive_registered_sources,
        "fetch_text",
        lambda url, timeout=30: "<html><head><title>Agency / X</title></head></html>",
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"sources": [x_source()]}), encoding="utf-8")

    report = build_report(
        argparse.Namespace(
            manifest=manifest,
            report=tmp_path / "report.json",
            source_type="x",
            agency_id="",
            include_blocked=True,
            dry_run=False,
            raw_root=tmp_path / "raw",
            normalized_root=tmp_path / "normalized",
            manual_seed_root=tmp_path / "manual_archive_seeds",
            max_x_posts=25,
            fetch_timeout=30,
        )
    )

    assert report["summary"]["status_counts"] == {"public_snapshot_captured": 1}


def test_archive_public_profile_snapshot_source_supports_facebook(tmp_path, monkeypatch):
    result = archive_public_profile_snapshot_source(
        {
            "source_id": "agency-facebook",
            "agency_id": "agency",
            "platform": "facebook",
            "source_type": "social_profile",
            "url": "https://www.facebook.com/agency",
            "account": "agency",
        },
        "facebook",
        raw_root=tmp_path / "raw",
        normalized_root=tmp_path / "normalized",
        fetcher=lambda url, timeout=30: "<html><head><title>Agency / Facebook</title><meta property='og:description' content='Official updates on Facebook'></head></html>",
    )

    assert result["status"] == "public_snapshot_captured"
    assert list((tmp_path / "raw" / "facebook_public_snapshot" / "2026-07").glob("*.json"))
    record = json.loads((tmp_path / "normalized" / "facebook" / "2026-07.jsonl").read_text(encoding="utf-8"))
    assert record["source_platform"] == "facebook"
    assert record["source_kind"] == "public_profile_snapshot"
    assert record["extraction_method"] == "facebook_public_web_snapshot"


def test_archive_public_profile_snapshot_source_supports_instagram(tmp_path):
    result = archive_public_profile_snapshot_source(
        {
            "source_id": "agency-instagram",
            "agency_id": "agency",
            "platform": "instagram",
            "source_type": "social_profile",
            "url": "https://www.instagram.com/agency/",
            "account": "agency",
        },
        "instagram",
        raw_root=tmp_path / "raw",
        normalized_root=tmp_path / "normalized",
        fetcher=lambda url, timeout=30: "<html><head><title>Agency / Instagram</title><meta property='og:site_name' content='Instagram'></head></html>",
    )

    assert result["status"] == "public_snapshot_captured"
    assert list((tmp_path / "raw" / "instagram_public_snapshot" / "2026-07").glob("*.json"))
    record = json.loads((tmp_path / "normalized" / "instagram" / "2026-07.jsonl").read_text(encoding="utf-8"))
    assert record["source_platform"] == "instagram"
    assert record["source_kind"] == "public_profile_snapshot"
    assert record["extraction_method"] == "instagram_public_web_snapshot"


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


def test_archive_threads_api_disabled_uses_public_snapshot_when_no_seed(tmp_path, monkeypatch):
    monkeypatch.delenv("THREADS_API_CAPTURE_ENABLED", raising=False)
    monkeypatch.setattr(
        archive_registered_sources,
        "fetch_text",
        lambda url, timeout=30: "<html><head><title>Threads / Agency</title><meta property='og:description' content='Public Threads snapshot'></head></html>",
    )
    manifest = write_threads_manifest(tmp_path)

    report = build_report(report_args(tmp_path, manifest))

    assert report["summary"]["status_counts"] == {"public_snapshot_captured": 1}
    result = report["results"][0]
    assert result["status"] == "public_snapshot_captured"
    assert list((tmp_path / "raw" / "threads_public_snapshot" / "2026-07").glob("*.json"))
    record = json.loads((tmp_path / "normalized" / "threads" / "2026-07.jsonl").read_text(encoding="utf-8"))
    assert record["source_platform"] == "threads"
    assert record["source_kind"] == "public_profile_snapshot"
    assert record["extraction_method"] == "threads_public_web_snapshot"


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
    monkeypatch.setattr(
        archive_registered_sources,
        "fetch_text",
        lambda url, timeout=30: "<html><head><title>Threads / Agency</title></head></html>",
    )
    manifest = write_threads_manifest(tmp_path)

    def unexpected_urlopen(request, timeout=30):
        raise AssertionError("Threads API should not be called when capture is disabled")

    monkeypatch.setattr(archive_registered_sources, "urlopen", unexpected_urlopen)

    report = build_report(report_args(tmp_path, manifest))

    assert report["summary"]["status_counts"] == {"public_snapshot_captured": 1}
    assert report["results"][0]["status"] == "public_snapshot_captured"
    assert report["results"][0]["status"] not in {"threads_permission_error", "threads_api_error"}

def test_archive_youtube_video_source_reports_blocked_metadata(tmp_path):
    def blocked(_url):
        raise HTTPError("https://www.youtube.com/oembed", 401, "Unauthorized", hdrs=None, fp=None)

    results = archive_registered_sources.archive_youtube_video_source(
        {
            "source_id": "agency-youtube-video",
            "agency_id": "agency",
            "platform": "youtube",
            "source_type": "social_profile",
            "url": "https://www.youtube.com/watch?v=abc123",
        },
        raw_root=tmp_path / "raw",
        normalized_root=tmp_path / "normalized",
        metadata_fetcher=blocked,
    )

    assert results[0]["status"] == "youtube_video_metadata_blocked"

