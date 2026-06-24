import argparse
import json

from scripts.archive_registered_sources import build_report


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
        )
    )

    assert report["summary"]["selected_sources"] == 3
    assert report["summary"]["status_counts"] == {
        "invoked": 1,
        "pending_adapter": 1,
        "unsupported_now": 1,
    }
    assert report["courts_current_sources_report"] == {
        "dry_run": True,
        "selected_supported_courts_sources": 1,
    }
