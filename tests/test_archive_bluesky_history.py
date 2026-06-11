from scripts.archive_bluesky_history import build_frequency_report


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
