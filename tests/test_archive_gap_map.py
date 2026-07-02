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
