import json

from src.archiver import archive_post
from scripts.archive_bluesky_history import build_frequency_report, build_gap_report


def test_build_frequency_report_counts_months_and_costs() -> None:
    report = build_frequency_report(
        [
            {"created_at": "2026-06-01T00:00:00.000Z"},
            {"created_at": "2026-06-01T01:00:00.000Z"},
            {"created_at": "2026-07-01T00:00:00.000Z"},
        ]
    )

    assert report["total_posts"] == 3
    assert report["date_range"] == {"start": "2026-06-01", "end": "2026-07-01"}
    assert report["posts_by_year"] == {"2026": 3}
    assert report["posts_by_month"][0]["month"] == "2026-06"
    assert report["posts_by_month"][0]["posts"] == 2
    assert report["posts_by_month"][0]["estimated_x_api_cost_with_source_url_usd"] == 0.4
    assert report["estimated_total_x_api_cost_without_url_usd"] == 0.045
    assert report["peak_post_day"] == {"date": "2026-06-01", "posts": 2}


def test_build_gap_report_lists_missing_archives(tmp_path) -> None:
    archive_post(
        agency="courtsofnz.bsky.social",
        post_id="archived",
        content="Archived",
        created_at="2026-06-01T00:00:00.000Z",
        media_urls=[],
        archive_dir=tmp_path,
    )

    report = build_gap_report(
        [
            {"post_id": "archived", "created_at": "2026-06-01T00:00:00.000Z"},
            {"post_id": "missing", "created_at": "2026-06-02T00:00:00.000Z"},
        ],
        handle="courtsofnz.bsky.social",
        archive_dir=str(tmp_path),
    )

    assert report["fetched_count"] == 2
    assert report["archived_count"] == 1
    assert report["missing_count"] == 1
    assert report["missing_post_ids"] == ["missing"]
    assert json.dumps(report)
