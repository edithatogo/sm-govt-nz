import json
from collections import Counter
from pathlib import Path

from scripts.build_archive_completion_matrix import (
    COMPLETE_STATES,
    build_completion_matrix,
    build_report_index,
    classify_state,
    dispatch_for,
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
    assert queue["items"][0]["dispatch"]["inputs"]["agency_id"] == "b"
    assert validate_matrix(matrix) == []


def test_public_platform_report_matches_candidate_by_canonical_url(tmp_path: Path) -> None:
    conductor = tmp_path / "conductor"
    conductor.mkdir()
    (conductor / "archive_publication_status.json").write_text("{}", encoding="utf-8")
    readiness = {
        "total_sources": 1,
        "sources": [{
            "source_id": "candidate-linkedin",
            "platform": "linkedin",
            "source_type": "social_profile",
            "url": "https://www.linkedin.com/company/example",
            "readiness": "registered",
        }],
    }
    manifest = {"sources": [{
        "source_id": "registered-linkedin",
        "platform": "linkedin",
        "url": "https://www.linkedin.com/company/example/",
    }]}
    reports = {
        "registered-linkedin": {
            "source_id": "registered-linkedin",
            "url": "https://www.linkedin.com/company/example",
            "status": "public_snapshot_captured",
            "evidence_report": "linkedin_archive_report.json",
        }
    }

    matrix, queue = build_completion_matrix(
        readiness, manifest, reports, Counter(), conductor
    )

    assert matrix["sources"][0]["completion_state"] == "archived"
    assert matrix["sources"][0]["latest_status"] == "public_snapshot_captured"
    assert queue["summary"]["queue_count"] == 0


def test_url_report_matching_prefers_success_over_onboarding_fallback(tmp_path: Path) -> None:
    conductor = tmp_path / "conductor"
    conductor.mkdir()
    (conductor / "archive_publication_status.json").write_text("{}", encoding="utf-8")
    readiness = {
        "total_sources": 1,
        "sources": [{
            "source_id": "candidate-linkedin",
            "platform": "linkedin",
            "source_type": "social_profile",
            "url": "https://www.linkedin.com/company/example",
            "readiness": "registered",
        }],
    }
    manifest = {"sources": readiness["sources"]}
    reports = {
        "onboarding": {
            "source_id": "onboarding-id",
            "url": "https://www.linkedin.com/company/example/",
            "status": "public_fallback_available",
            "evidence_report": "manual_seed_onboarding_report.json",
        },
        "capture": {
            "source_id": "registered-id",
            "url": "https://www.linkedin.com/company/example",
            "status": "public_snapshot_captured",
            "evidence_report": "linkedin_archive_report.json",
        },
    }

    matrix, _queue = build_completion_matrix(
        readiness, manifest, reports, Counter(), conductor
    )

    assert matrix["sources"][0]["completion_state"] == "archived"
    assert matrix["sources"][0]["latest_status"] == "public_snapshot_captured"


def test_url_report_matching_can_override_lower_ranked_direct_source_report(tmp_path: Path) -> None:
    conductor = tmp_path / "conductor"
    conductor.mkdir()
    (conductor / "archive_publication_status.json").write_text("{}", encoding="utf-8")
    readiness = {
        "total_sources": 1,
        "sources": [{
            "source_id": "candidate-linkedin",
            "platform": "linkedin",
            "source_type": "social_profile",
            "url": "https://www.linkedin.com/company/example",
            "readiness": "registered",
        }],
    }
    manifest = {"sources": readiness["sources"]}
    reports = {
        "candidate-linkedin": {
            "source_id": "candidate-linkedin",
            "url": "https://www.linkedin.com/company/example",
            "status": "public_fallback_available",
            "evidence_report": "manual_seed_onboarding_report.json",
        },
        "registered-linkedin": {
            "source_id": "registered-linkedin",
            "url": "https://www.linkedin.com/company/example/",
            "status": "http_error",
            "reason": "HTTP 999: blocked",
            "evidence_report": "linkedin_archive_report.json",
        },
    }

    matrix, _queue = build_completion_matrix(
        readiness, manifest, reports, Counter(), conductor
    )

    assert matrix["sources"][0]["completion_state"] == "terminal_external_access"
    assert matrix["sources"][0]["latest_status"] == "http_error"


def test_generated_workflow_is_daily_bounded_and_monthly_guarded() -> None:
    workflow = Path(".github/workflows/archive_completion_loop.yml").read_text(encoding="utf-8")
    assert 'cron: "41 4 * * *"' in workflow
    assert "scripts/build_archive_completion_matrix.py" in workflow
    assert "scripts/dispatch_archive_completion_queue.py" in workflow
    assert "--max-actions" in workflow
    assert "gh workflow run publish_archives.yml" in workflow
    assert "publication_target=all" in workflow
    assert "publish_archive_release.py" not in workflow
    assert "automation_faults" in workflow


def test_registered_source_workflow_serializes_shared_source_type_state() -> None:
    workflow = Path(".github/workflows/archive_registered_sources.yml").read_text(encoding="utf-8")
    assert "inputs.source_type || 'scheduled'" in workflow
    assert "inputs.agency_id || 'all'" not in workflow
    assert "cancel-in-progress: false" in workflow


def test_matrix_discovers_agency_sharded_reports(tmp_path: Path) -> None:
    conductor = tmp_path / "conductor"
    conductor.mkdir()
    report = conductor / "linkedin_archive_aut-university_report.json"
    report.write_text(json.dumps({
        "results": [{
            "source_id": "aut-source",
            "url": "https://www.linkedin.com/company/aut",
            "status": "http_error",
            "reason": "HTTP 999: blocked",
        }]
    }), encoding="utf-8")

    indexed = build_report_index(conductor)

    assert indexed["aut-source"]["status"] == "http_error"


def test_website_fallback_dispatches_canonical_publication_workflow() -> None:
    workflow = Path(".github/workflows/archive_website_browser_fallback.yml").read_text(
        encoding="utf-8"
    )
    assert "actions: write" in workflow
    assert "gh workflow run publish_archives.yml" in workflow
    assert "publish_archive_release.py" not in workflow


def test_prior_terminal_evidence_survives_sharded_report_regression(tmp_path: Path) -> None:
    conductor = tmp_path / "conductor"
    conductor.mkdir()
    (conductor / "archive_publication_status.json").write_text("{}", encoding="utf-8")
    readiness = {
        "total_sources": 1,
        "sources": [{"source_id": "rss", "platform": "rss", "source_type": "rss", "readiness": "resolver_ok"}],
    }
    manifest = {"sources": readiness["sources"]}
    prior = {
        "sources": [{
            "source_id": "rss", "completion_state": "archived", "blocker_class": "archive_evidence",
            "record_count": 4, "archive_evidence": ["old-report.json"],
            "publication_evidence": ["old-publication.json"],
        }]
    }

    matrix, _queue = build_completion_matrix(
        readiness,
        manifest,
        {"rss": {"source_id": "rss", "status": "needs_authorized_seed_or_api", "evidence_report": "new-report.json"}},
        Counter(),
        conductor,
        prior_matrix=prior,
    )

    row = matrix["sources"][0]
    assert row["completion_state"] == "archived"
    assert row["record_count"] == 4
    assert "old-report.json" in row["archive_evidence"]


def test_prior_archive_evidence_survives_candidate_identity_drift(tmp_path: Path) -> None:
    conductor = tmp_path / "conductor"
    conductor.mkdir()
    (conductor / "archive_publication_status.json").write_text("{}", encoding="utf-8")
    readiness = {
        "total_sources": 1,
        "sources": [{
            "candidate_id": "candidate-new", "source_id": "registered-source",
            "platform": "linkedin", "source_type": "social_profile",
            "url": "https://www.linkedin.com/company/example/", "readiness": "resolver_ok",
        }],
    }
    manifest = {"sources": [{
        "source_id": "registered-source", "platform": "linkedin",
        "url": "https://www.linkedin.com/company/example",
    }]}
    prior = {"sources": [{
        "candidate_id": "candidate-old", "source_id": "registered-source",
        "url": "https://www.linkedin.com/company/example", "completion_state": "archived",
        "blocker_class": "archive_evidence", "record_count": 1,
        "archive_evidence": ["old-report.json"],
        "publication_evidence": ["old-publication.json"],
    }]}

    matrix, _queue = build_completion_matrix(
        readiness,
        manifest,
        {"candidate-new": {"candidate_id": "candidate-new", "status": "http_error"}},
        Counter(),
        conductor,
        prior_matrix=prior,
    )

    row = matrix["sources"][0]
    assert row["completion_state"] == "archived"
    assert row["historical_capture_state"] == "evidence_present"
    assert row["record_count"] == 1


def test_new_seed_reopens_prior_external_access_state(tmp_path: Path) -> None:
    conductor = tmp_path / "conductor"
    conductor.mkdir()
    readiness = {
        "total_sources": 1,
        "sources": [{"source_id": "x", "platform": "x", "source_type": "social_profile", "readiness": "blocked_credential"}],
    }
    manifest = {"sources": readiness["sources"]}
    prior = {"sources": [{"source_id": "x", "completion_state": "terminal_external_access"}]}
    reports = {"x": {"source_id": "x", "status": "seed_present", "evidence_report": "seed.json"}}

    matrix, _queue = build_completion_matrix(
        readiness, manifest, reports, Counter(), conductor, prior_matrix=prior
    )

    assert matrix["sources"][0]["completion_state"] == "scheduled"


def test_completion_schema_accepts_only_declared_states() -> None:
    schema = json.loads(Path("conductor/archive_completion_matrix.schema.json").read_text(encoding="utf-8"))
    states = schema["properties"]["sources"]["items"]["properties"]["completion_state"]["enum"]
    assert set(states) == {
        "discovered", "rejected_not_government", "registered", "scheduled", "capturing",
        "archived", "terminal_empty", "terminal_deleted", "terminal_invalid",
        "terminal_external_access", "automation_fault",
    }


def test_dispatch_offsets_are_bounded_and_shard_specific() -> None:
    linkedin = dispatch_for(
        {"platform": "linkedin", "_manifest_offset": 237}, "scheduled"
    )
    website = dispatch_for(
        {"platform": "website_page", "_queue_offset": 27}, "automation_fault"
    )

    assert linkedin["inputs"]["offset_sources"] == "200"
    linkedin["inputs"]["agency_id"] = "example-agency"
    linkedin["inputs"]["offset_sources"] = "237"
    targeted = dispatch_for(
        {"platform": "linkedin", "agency_id": "example-agency", "_manifest_offset": 237}, "scheduled"
    )
    assert targeted["inputs"]["agency_id"] == "example-agency"
    assert targeted["inputs"]["offset_sources"] == "0"
    assert website["inputs"]["offset_sources"] == "20"


def test_processed_empty_seed_outranks_stale_seed_presence() -> None:
    assert classify_state(
        {"platform": "x", "readiness": "blocked_credential"},
        True,
        {"status": "seed_empty"},
        0,
    )[0] == "terminal_invalid"


def test_linkedin_public_rate_limit_is_monitored_external_access() -> None:
    state, blocker = classify_state(
        {"platform": "linkedin", "readiness": "resolver_ok"},
        True,
        {"status": "http_error", "reason": "HTTP 429: Too Many Requests"},
        0,
    )
    assert state == "terminal_external_access"
    assert blocker == "linkedin_public_access_rate_limited"


def test_unattempted_registered_website_uses_http_capture_first() -> None:
    dispatch = dispatch_for(
        {"platform": "website_page", "_manifest_offset": 437}, "scheduled"
    )
    assert dispatch["workflow"] == "archive_registered_sources.yml"
    assert dispatch["inputs"]["source_type"] == "website_page"
    assert dispatch["inputs"]["offset_sources"] == "400"


def test_exhausted_heuristic_endpoint_is_terminal_invalid() -> None:
    state, blocker = classify_state(
        {"platform": "rss", "origin": "configured_common_path"},
        True,
        {"status": "capture_failed"},
        0,
    )
    assert state == "terminal_invalid"
    assert blocker == "heuristic_endpoint_exhausted_public_retries"


def test_exhausted_website_fallback_is_terminal_external_access() -> None:
    state, blocker = classify_state(
        {"platform": "website_page", "origin": "registered"},
        True,
        {"status": "network_error"},
        0,
    )
    assert state == "terminal_external_access"
    assert blocker == "website_exhausted_http_and_browser_fallbacks"
