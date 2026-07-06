import argparse
import json
from pathlib import Path

from scripts.archive_website_browser import (
    build_report,
    detect_browser_status,
    html_to_visible_text,
    select_sources,
    write_summary,
)


def test_html_to_visible_text_removes_scripts_and_tags():
    html = "<html><script>secret()</script><body><h1>Title</h1><p>Visible &amp; public</p></body></html>"

    text = html_to_visible_text(html)

    assert "secret" not in text
    assert "Title" in text
    assert "Visible & public" in text


def test_detect_browser_status_identifies_captcha_challenge():
    assert detect_browser_status("Checking your browser before accessing", "") == (
        "browser_captcha_or_challenge",
        "Checking your browser",
    )


def test_select_sources_uses_triage_eligible_statuses(tmp_path):
    manifest = {
        "sources": [
            {"source_id": "blocked", "agency_id": "a", "platform": "website_page", "source_type": "website_page", "url": "https://agency.example"},
            {"source_id": "retired", "agency_id": "a", "platform": "website_page", "source_type": "website_page", "url": "https://retired.example"},
            {"source_id": "rss", "agency_id": "a", "platform": "rss", "source_type": "rss_feed", "url": "https://agency.example/rss"},
        ]
    }
    triage = tmp_path / "triage.json"
    triage.write_text(
        json.dumps(
            {
                "items": [
                    {"source_id": "blocked", "platform": "website_page", "status": "capture_blocked"},
                    {"source_id": "retired", "platform": "website_page", "status": "not_found"},
                ]
            }
        ),
        encoding="utf-8",
    )

    selected = select_sources(
        manifest,
        agency_id="",
        triage_report=triage,
        eligible_statuses={"capture_blocked"},
        include_without_triage=False,
    )

    assert [source["source_id"] for source in selected] == ["blocked"]
    assert selected[0]["browser_fallback_trigger"]["status"] == "capture_blocked"
    assert selected[0]["candidate_id"] == "blocked"


def test_select_sources_matches_triage_candidate_ids(tmp_path):
    manifest = {
        "sources": [
            {
                "candidate_id": "candidate-123",
                "source_id": "manifest-abc",
                "agency_id": "a",
                "platform": "website_page",
                "source_type": "website_page",
                "url": "https://agency.example",
            }
        ]
    }
    triage = tmp_path / "triage.json"
    triage.write_text(
        json.dumps(
            {
                "items": [
                    {"source_id": "candidate-123", "platform": "website_page", "status": "capture_blocked"}
                ]
            }
        ),
        encoding="utf-8",
    )

    selected = select_sources(
        manifest,
        agency_id="",
        triage_report=triage,
        eligible_statuses={"capture_blocked"},
        include_without_triage=False,
    )

    assert [source["source_id"] for source in selected] == ["manifest-abc"]
    assert selected[0]["browser_fallback_trigger"]["status"] == "capture_blocked"
    assert selected[0]["candidate_id"] == "candidate-123"


def test_fixture_capture_writes_raw_and_normalized(tmp_path):
    manifest = tmp_path / "manifest.json"
    triage = tmp_path / "triage.json"
    manifest.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "source_id": "blocked",
                        "agency_id": "agency",
                        "agency_name": "Agency",
                        "platform": "website_page",
                        "source_type": "website_page",
                        "url": "https://agency.example/news",
                        "account": "Agency",
                        "archive_status": "ready",
                        "feasibility": "high",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    triage.write_text(json.dumps({"items": [{"source_id": "blocked", "platform": "website_page", "status": "capture_blocked"}]}), encoding="utf-8")

    report = build_report(
        argparse.Namespace(
            manifest=manifest,
            triage_report=triage,
            report=tmp_path / "report.json",
            summary=tmp_path / "summary.md",
            raw_root=tmp_path / "raw",
            normalized_root=tmp_path / "normalized",
            agency_id="",
            offset_sources=0,
            limit_sources=10,
            eligible_statuses="capture_blocked",
            include_without_triage=False,
            dry_run=False,
            fixture_html="<html><body><main>Rendered public government page</main></body></html>",
            per_page_timeout=1,
            wait_after_load_ms=0,
            screenshot=False,
        )
    )

    assert report["summary"]["status_counts"] == {"browser_captured": 1}
    assert list((tmp_path / "raw" / "website_browser").glob("*/*.json"))
    normalized = list((tmp_path / "normalized" / "website").glob("*.jsonl"))[0].read_text(encoding="utf-8")
    assert "Rendered public government page" in normalized
    assert "playwright_public_browser_fallback" in normalized


def test_fixture_capture_records_access_marker_without_normalized_record(tmp_path):
    manifest = tmp_path / "manifest.json"
    triage = tmp_path / "triage.json"
    manifest.write_text(
        json.dumps({"sources": [{"source_id": "blocked", "agency_id": "agency", "platform": "website_page", "source_type": "website_page", "url": "https://agency.example"}]}),
        encoding="utf-8",
    )
    triage.write_text(json.dumps({"items": [{"source_id": "blocked", "platform": "website_page", "status": "capture_blocked"}]}), encoding="utf-8")

    report = build_report(
        argparse.Namespace(
            manifest=manifest,
            triage_report=triage,
            report=tmp_path / "report.json",
            summary=tmp_path / "summary.md",
            raw_root=tmp_path / "raw",
            normalized_root=tmp_path / "normalized",
            agency_id="",
            offset_sources=0,
            limit_sources=10,
            eligible_statuses="capture_blocked",
            include_without_triage=False,
            dry_run=False,
            fixture_html="<html><body>Access denied</body></html>",
            per_page_timeout=1,
            wait_after_load_ms=0,
            screenshot=False,
        )
    )

    assert report["summary"]["status_counts"] == {"browser_access_blocked": 1}
    assert not (tmp_path / "normalized" / "website").exists()


def test_website_browser_workflow_is_bounded_and_guarded():
    workflow = Path(".github/workflows/archive_website_browser_fallback.yml").read_text(encoding="utf-8")

    assert "limit_sources" in workflow
    assert "offset_sources" in workflow
    assert "xvfb-run -a python -m scripts.archive_website_browser" in workflow
    assert 'if [ -n "$AGENCY_ID" ]; then' in workflow
    assert "--triage-report conductor/website_archive_failure_triage_report.json" in workflow
    assert "--report conductor/website_browser_archive_report.json" in workflow
    assert "--output conductor/website_archive_gap_map.json" in workflow
    assert "publish == 'true'" in workflow
    assert "playwright install chromium" in workflow


def test_summary_mentions_guardrails(tmp_path):
    report = {"generated_at": "2026-07-02T00:00:00+00:00", "summary": {"selected_sources": 0, "result_count": 0, "status_counts": {}}}
    summary = tmp_path / "summary.md"

    write_summary(summary, report)

    assert "No login, CAPTCHA solving, proxies" in summary.read_text(encoding="utf-8")

def test_live_capture_source_code_opens_a_fresh_page_per_source():
    source = Path("scripts/archive_website_browser.py").read_text(encoding="utf-8")

    assert "for source in sources:\n            page = context.new_page()" in source
    assert "finally:\n                page.close()" in source

