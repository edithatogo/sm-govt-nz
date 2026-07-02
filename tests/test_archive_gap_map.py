import json

from scripts.build_archive_gap_map import build_gap_map


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

