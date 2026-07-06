import json
from pathlib import Path

from scripts.build_archive_gap_map import build_gap_map, default_reports


def test_gap_map_prioritizes_seed_and_fixable_gaps(tmp_path):
    report = tmp_path / "report.json"
    report.write_text(
        json.dumps(
            {
                "summary": {"selected_sources": 3},
                "results": [
                    {"source_id": "ok", "platform": "rss", "status": "captured"},
                    {"source_id": "seed", "platform": "linkedin", "status": "manual_seed_missing"},
                    {"source_id": "bad-url", "platform": "youtube", "status": "capture_failed"},
                ],
            }
        ),
        encoding="utf-8",
    )

    gap_map = build_gap_map([report])

    assert gap_map["summary"]["gap_count"] == 2
    assert gap_map["summary"]["priority_counts"]["archived_or_already_archived"] == 1
    assert gap_map["summary"]["priority_counts"]["p1_existing_resources"] == 1
    assert gap_map["summary"]["priority_counts"]["p2_existing_system_needs_seed_input"] == 1
    assert {item["source_id"]: item["priority"] for item in gap_map["gaps"]} == {
        "bad-url": "p1_existing_resources",
        "seed": "p2_existing_system_needs_seed_input",
    }

def test_gap_map_supersedes_http_website_gap_with_browser_success(tmp_path):
    http_report = tmp_path / "website_archive_report.json"
    browser_report = tmp_path / "website_browser_archive_report.json"
    http_report.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "source_id": "agency-web",
                        "platform": "website_page",
                        "status": "capture_blocked",
                        "reason": "HTTP 403",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    browser_report.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "source_id": "agency-web",
                        "platform": "website_page",
                        "status": "browser_captured",
                        "reason": "captured public rendered website content",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    gap_map = build_gap_map([http_report, browser_report])

    assert gap_map["summary"]["gap_count"] == 0
    assert gap_map["summary"]["priority_counts"] == {"archived_or_already_archived": 1}
    assert gap_map["summary"]["status_counts"] == {"browser_captured": 1}
    assert gap_map["summary"]["input_status_counts"] == {"browser_captured": 1, "capture_blocked": 1}
    assert gap_map["summary"]["superseded_source_count"] == 1


def test_gap_map_supersedes_candidate_id_browser_success(tmp_path):
    http_report = tmp_path / "website_archive_report.json"
    browser_report = tmp_path / "website_browser_archive_report.json"
    http_report.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "source_id": "web-candidate",
                        "platform": "website_page",
                        "status": "not_acceptable",
                        "reason": "HTTP 406",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    browser_report.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "candidate_id": "web-candidate",
                        "source_id": "manifest-source",
                        "platform": "website_page",
                        "status": "browser_captured",
                        "reason": "captured public rendered website content",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    gap_map = build_gap_map([http_report, browser_report])

    assert gap_map["summary"]["gap_count"] == 0
    assert gap_map["summary"]["priority_counts"] == {"archived_or_already_archived": 1}
    assert gap_map["summary"]["status_counts"] == {"browser_captured": 1}


def test_gap_map_keeps_browser_challenge_as_report_only(tmp_path):
    report = tmp_path / "website_browser_archive_report.json"
    report.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "source_id": "agency-web",
                        "platform": "website_page",
                        "status": "browser_captcha_or_challenge",
                        "reason": "cloudflare",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    gap_map = build_gap_map([report])

    assert gap_map["summary"]["gap_count"] == 0
    assert gap_map["summary"]["priority_counts"] == {"monitor_report_only": 1}


def test_gap_map_keeps_blocked_youtube_video_metadata_as_report_only(tmp_path):
    report = tmp_path / "youtube_archive_report.json"
    report.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "source_id": "yt-video",
                        "platform": "youtube",
                        "status": "youtube_video_metadata_blocked",
                        "reason": "HTTP 401: YouTube video metadata unavailable",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    gap_map = build_gap_map([report])

    assert gap_map["summary"]["gap_count"] == 0
    assert gap_map["summary"]["priority_counts"] == {"monitor_report_only": 1}
    assert gap_map["summary"]["status_counts"] == {"youtube_video_metadata_blocked": 1}


def test_default_reports_excludes_stale_offset_shards(tmp_path, monkeypatch):
    conductor = tmp_path / "conductor"
    conductor.mkdir()
    (conductor / "youtube_archive_report.json").write_text("{}", encoding="utf-8")
    (conductor / "youtube_archive_offset_100_report.json").write_text("{}", encoding="utf-8")
    (conductor / "linkedin_archive_offset_100_report.json").write_text("{}", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    reports = [Path(path).as_posix() for path in default_reports()]

    assert reports == ["conductor/youtube_archive_report.json"]


def test_gap_map_reads_manual_seed_onboarding_items(tmp_path):
    report = tmp_path / "manual_seed_onboarding_report.json"
    report.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "source_id": "agency-facebook",
                        "agency_id": "agency",
                        "platform": "facebook",
                        "onboarding_status": "needs_authorized_seed_or_api",
                    },
                    {
                        "source_id": "agency-x",
                        "agency_id": "agency",
                        "platform": "x",
                        "onboarding_status": "seed_present",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    gap_map = build_gap_map([report])

    assert gap_map["summary"]["gap_count"] == 1
    assert gap_map["summary"]["priority_counts"]["p2_existing_system_needs_seed_input"] == 1
    assert gap_map["gaps"][0]["source_id"] == "agency-facebook"

