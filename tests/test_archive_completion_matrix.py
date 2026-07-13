import json
from collections import Counter
from pathlib import Path

from scripts.build_archive_completion_matrix import (
    COMPLETE_STATES,
    build_completion_matrix,
    classify_state,
    validate_matrix,
)


def test_seed_present_and_workflow_setup_are_not_archived() -> None:
    row = {"platform": "x", "readiness": "blocked_credential"}
    assert classify_state(row, True, {"status": "seed_present"}, 0)[0] == "scheduled"
    assert classify_state(row, True, {}, 0)[0] == "terminal_external_access"


def test_completion_states_cover_archive_and_terminal_evidence() -> None:
    assert "archived" in COMPLETE_STATES
    assert "terminal_empty" in COMPLETE_STATES
    assert "terminal_deleted" in COMPLETE_STATES
    assert "terminal_invalid" in COMPLETE_STATES
    assert "terminal_external_access" in COMPLETE_STATES
    assert "scheduled" not in COMPLETE_STATES
    assert "automation_fault" not in COMPLETE_STATES


def test_matrix_reconciles_all_readiness_rows_and_orders_work(tmp_path: Path) -> None:
    conductor = tmp_path / "conductor"
    conductor.mkdir()
    (conductor / "archive_publication_status.json").write_text("{}", encoding="utf-8")
    readiness = {
        "total_sources": 4,
        "sources": [
            {"source_id": "yt", "agency_id": "a", "platform": "youtube", "source_type": "youtube", "url": "https://youtube.example", "readiness": "resolver_ok"},
            {"source_id": "li", "agency_id": "b", "platform": "linkedin", "source_type": "social_profile", "url": "https://linkedin.example", "readiness": "blocked_credential"},
            {"source_id": "fb", "agency_id": "c", "platform": "facebook", "source_type": "social_profile", "url": "https://facebook.example", "readiness": "blocked_credential"},
            {"source_id": "rss", "agency_id": "d", "platform": "rss", "source_type": "rss", "url": "https://example/rss", "readiness": "resolver_ok"},
        ],
    }
    manifest = {"sources": readiness["sources"]}
    reports = {
        "yt": {"source_id": "yt", "status": "youtube_video_not_found", "evidence_report": "yt.json"},
        "li": {"source_id": "li", "status": "public_fallback_available", "evidence_report": "li.json"},
        "fb": {"source_id": "fb", "status": "needs_authorized_seed_or_api", "evidence_report": "seed.json"},
        "rss": {"source_id": "rss", "status": "captured", "evidence_report": "rss.json"},
    }

    matrix, queue = build_completion_matrix(readiness, manifest, reports, Counter(), conductor)

    assert matrix["summary"]["total_candidates"] == 4
    by_id = {row["source_id"]: row for row in matrix["sources"]}
    assert by_id["yt"]["completion_state"] == "terminal_deleted"
    assert by_id["li"]["completion_state"] == "scheduled"
    assert by_id["fb"]["completion_state"] == "terminal_external_access"
    assert by_id["rss"]["completion_state"] == "archived"
    assert [item["source_id"] for item in queue["items"]] == ["li"]
    assert queue["items"][0]["dispatch"]["inputs"]["agency_id"] == ""
    assert validate_matrix(matrix) == []


def test_generated_workflow_is_daily_bounded_and_monthly_guarded() -> None:
    workflow = Path(".github/workflows/archive_completion_loop.yml").read_text(encoding="utf-8")
    assert 'cron: "41 4 * * *"' in workflow
    assert "scripts/build_archive_completion_matrix.py" in workflow
    assert "scripts/dispatch_archive_completion_queue.py" in workflow
    assert "--max-actions" in workflow
    assert "--monthly-guard" in workflow
    assert "automation_faults" in workflow


def test_completion_schema_accepts_only_declared_states() -> None:
    schema = json.loads(Path("conductor/archive_completion_matrix.schema.json").read_text(encoding="utf-8"))
    states = schema["properties"]["sources"]["items"]["properties"]["completion_state"]["enum"]
    assert set(states) == {
        "discovered", "rejected_not_government", "registered", "scheduled", "capturing",
        "archived", "terminal_empty", "terminal_deleted", "terminal_invalid",
        "terminal_external_access", "automation_fault",
    }
