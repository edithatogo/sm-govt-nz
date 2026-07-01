import json

from scripts.build_archive_failure_triage_report import build_report, main


def test_archive_failure_triage_report_extracts_non_success_rows(tmp_path):
    report_path = tmp_path / "youtube_report.json"
    report_path.write_text(
        json.dumps(
            {
                "generated_at": "2026-07-01T00:00:00+00:00",
                "dry_run": False,
                "summary": {"selected_sources": 2},
                "results": [
                    {
                        "source_id": "ok",
                        "agency_id": "agency",
                        "platform": "youtube",
                        "url": "https://www.youtube.com/@ok",
                        "status": "captured",
                    },
                    {
                        "source_id": "bad",
                        "agency_id": "agency",
                        "platform": "youtube",
                        "url": "https://www.youtube.com/yt/about/policies/#community-guidelines",
                        "status": "capture_failed",
                        "reason": "could not resolve YouTube channel id",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    report = build_report([report_path])

    assert report["summary"]["failure_count"] == 1
    assert report["summary"]["status_counts"] == {"capture_failed": 1}
    item = report["items"][0]
    assert item["source_id"] == "bad"
    assert item["recommended_action"] == "review_url_or_adapter"
    assert "feedback_command" not in item


def test_archive_failure_triage_report_treats_youtube_no_records_as_report_only(tmp_path):
    report_path = tmp_path / "youtube_report.json"
    report_path.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "source_id": "empty",
                        "agency_id": "agency",
                        "platform": "youtube",
                        "url": "https://www.youtube.com/@empty",
                        "status": "no_records",
                        "reason": "YouTube channel RSS returned no entries",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    report = build_report([report_path])

    assert report["summary"]["failure_count"] == 0
    assert report["summary"]["report_only_count"] == 1
    assert report["summary"]["report_only_status_counts"] == {"no_records": 1}
    assert report["items"] == []
    assert report["report_only_items"][0]["recommended_action"] == "monitor_zero_record_channel"
    assert report["report_only_items"][0]["report_only"] is True


def test_archive_failure_triage_report_writes_output(tmp_path, monkeypatch):
    report_path = tmp_path / "website_report.json"
    output = tmp_path / "triage.json"
    report_path.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "source_id": "blocked",
                        "agency_id": "agency",
                        "platform": "website_page",
                        "url": "https://agency.example",
                        "status": "capture_blocked",
                        "reason": "HTTP 403: Forbidden",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "build_archive_failure_triage_report.py",
            "--report",
            str(report_path),
            "--output",
            str(output),
        ],
    )

    main()

    written = json.loads(output.read_text(encoding="utf-8"))
    assert written["summary"]["platform_counts"] == {"website_page": 1}
    assert written["items"][0]["recommended_action"] == "review_access_or_mark_blocked"


def test_archive_failure_triage_report_tolerates_schema_drift(tmp_path):
    scalar_report = tmp_path / "scalar.json"
    null_results_report = tmp_path / "null-results.json"
    scalar_report.write_text('"not an object"', encoding="utf-8")
    null_results_report.write_text('{"results": null}', encoding="utf-8")

    report = build_report([scalar_report, null_results_report])

    assert report["summary"]["failure_count"] == 0
    assert report["report_summaries"][str(scalar_report)]["summary"] == {}
