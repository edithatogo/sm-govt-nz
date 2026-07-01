from scripts.build_historical_backlog_matrix import build_matrix


def test_historical_backlog_matrix_batches_ready_and_candidate_sources() -> None:
    manifest = {
        "sources": [
            {"source_id": "rss-1", "platform": "rss", "archive_status": "ready"},
            {"source_id": "rss-2", "platform": "rss", "archive_status": "candidate"},
            {"source_id": "rss-3", "platform": "rss", "archive_status": "degraded"},
            {"source_id": "web-1", "platform": "website_page", "archive_status": "ready"},
        ]
    }

    matrix = build_matrix(
        manifest,
        source_types=["rss", "website_page", "youtube"],
        batch_size=1,
        max_batches=0,
    )

    assert matrix["summary"]["batch_count"] == 3
    assert matrix["summary"]["selected_source_counts"] == {
        "rss": 2,
        "website_page": 1,
        "youtube": 0,
    }
    assert [item["source_type"] for item in matrix["include"]] == [
        "rss",
        "rss",
        "website_page",
    ]
    assert [item["offset"] for item in matrix["include"]] == [0, 1, 0]


def test_historical_backlog_matrix_respects_max_batches() -> None:
    manifest = {
        "sources": [
            {"source_id": f"rss-{index}", "platform": "rss", "archive_status": "ready"}
            for index in range(250)
        ]
    }

    matrix = build_matrix(
        manifest,
        source_types=["rss"],
        batch_size=100,
        max_batches=2,
    )

    assert matrix["summary"]["batch_count"] == 2
    assert matrix["include"][0]["offset"] == 0
    assert matrix["include"][1]["offset"] == 100
