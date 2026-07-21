from scripts.build_source_candidate_issue import governed_identities, review_candidates


def test_governed_candidates_do_not_remain_issue_worthy() -> None:
    report = {
        "candidates": [
            {
                "candidate_id": "known",
                "source_type": "rss_feed",
                "url": "https://example.govt.nz/feed/",
                "archive_status": "ready",
            },
            {
                "candidate_id": "new",
                "source_type": "rss_feed",
                "url": "https://new.govt.nz/feed",
                "archive_status": "ready",
            },
        ]
    }
    governed = governed_identities(
        [{"sources": [{"source_id": "registered", "url": "https://example.govt.nz/feed"}]}]
    )

    assert [item["candidate_id"] for item in review_candidates(report, governed)] == ["new"]
