from scripts.apply_archive_failure_triage import apply_triage


def test_apply_archive_failure_triage_degrades_bad_youtube_and_blocked_website():
    manifest = {
        "sources": [
            {
                "source_id": "bad-youtube",
                "platform": "youtube",
                "archive_status": "candidate",
                "feasibility": "medium",
                "url": "https://www.youtube.com/watch?v=abc",
                "notes": "Existing note.",
            },
            {
                "source_id": "empty-youtube",
                "platform": "youtube",
                "archive_status": "candidate",
                "feasibility": "medium",
                "url": "https://www.youtube.com/@agency",
            },
            {
                "source_id": "blocked-website",
                "platform": "website_page",
                "archive_status": "ready",
                "feasibility": "high",
                "url": "https://agency.example",
            },
        ]
    }
    triage = {
        "items": [
            {
                "source_id": "bad-youtube",
                "platform": "youtube",
                "status": "capture_failed",
                "reason": "YouTube channel resolver failed: YouTube URL is not a channel URL",
            },
            {
                "source_id": "empty-youtube",
                "platform": "youtube",
                "status": "no_records",
                "reason": "YouTube channel RSS returned no entries",
            },
            {
                "source_id": "blocked-website",
                "platform": "website_page",
                "status": "capture_blocked",
                "reason": "HTTP 403: Forbidden",
            },
        ]
    }

    report = apply_triage(manifest, [triage])

    assert report["summary"]["changed_sources"] == 2
    by_id = {source["source_id"]: source for source in manifest["sources"]}
    assert by_id["bad-youtube"]["archive_status"] == "degraded"
    assert by_id["blocked-website"]["archive_status"] == "degraded"
    assert by_id["empty-youtube"]["archive_status"] == "candidate"
    assert manifest["summary"]["archive_status_counts"] == {"candidate": 1, "degraded": 2}
