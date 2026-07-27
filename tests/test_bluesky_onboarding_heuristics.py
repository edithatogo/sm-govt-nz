import json

import pytest

from src.bluesky_onboarding_heuristics import (
    choose_plan,
    default_state,
    load_pilot_report,
    rank_candidates,
    record_event,
    save_state,
)


def test_plan_is_deterministic_without_history() -> None:
    assert choose_plan(default_state()).name == "headed_uc_cdp"


def test_plan_scoring_ignores_non_plan_metadata() -> None:
    state = default_state()
    state["plans"]["schema_version"] = 1
    assert choose_plan(state).name == "headed_uc_cdp"


def test_learning_is_sanitized_and_persistent(tmp_path) -> None:
    state = default_state()
    event = record_event(state, "agency", "preflight_passed", "headed_uc_cdp")
    assert set(event) == {"mirror_id", "outcome", "plan", "recorded_at"}
    save_state(state, tmp_path / "state.json")
    assert "password" not in json.dumps(state).casefold()


def test_candidates_rank_failures_after_stable_rows() -> None:
    state = default_state()
    record_event(state, "blocked", "preflight_failed", "headed_uc_cdp")
    rows = {"mirrors": [
        {"mirror_id": "blocked", "lifecycle_state": "candidate"},
        {"mirror_id": "next", "lifecycle_state": "candidate"},
    ]}
    assert [row["mirror_id"] for row in rank_candidates(rows, state)] == ["next", "blocked"]


def test_candidates_prioritize_evidence_backed_pilot_report() -> None:
    state = default_state()
    rows = {"mirrors": [
        {"mirror_id": "airways", "lifecycle_state": "candidate"},
        {"mirror_id": "electoral", "lifecycle_state": "candidate"},
        {"mirror_id": "larger", "lifecycle_state": "candidate"},
    ]}
    report = {"candidates": [
        {"mirror_id": "electoral", "eligible_backlog": 1, "issue_number": 85},
        {"mirror_id": "larger", "eligible_backlog": 4, "issue_number": 98},
    ]}

    ranked = rank_candidates(rows, state, report)

    assert [row["mirror_id"] for row in ranked] == [
        "electoral",
        "larger",
        "airways",
    ]


def test_candidate_failures_remain_higher_order_safety_signal() -> None:
    state = default_state()
    record_event(state, "electoral", "blocked_external", "headed_uc_cdp")
    rows = {"mirrors": [
        {"mirror_id": "electoral", "lifecycle_state": "candidate"},
        {"mirror_id": "larger", "lifecycle_state": "candidate"},
    ]}
    report = {"candidates": [
        {"mirror_id": "electoral", "eligible_backlog": 1, "issue_number": 85},
        {"mirror_id": "larger", "eligible_backlog": 4, "issue_number": 98},
    ]}

    assert [row["mirror_id"] for row in rank_candidates(rows, state, report)] == [
        "larger",
        "electoral",
    ]


def test_ranked_candidate_requires_onboarding_issue() -> None:
    state = default_state()
    rows = {"mirrors": [
        {"mirror_id": "tracked", "lifecycle_state": "candidate"},
        {"mirror_id": "untracked", "lifecycle_state": "candidate"},
    ]}
    report = {"candidates": [
        {"mirror_id": "untracked", "eligible_backlog": 1, "issue_number": None},
        {"mirror_id": "tracked", "eligible_backlog": 4, "issue_number": 98},
    ]}

    assert [row["mirror_id"] for row in rank_candidates(rows, state, report)] == [
        "tracked",
        "untracked",
    ]


def test_invalid_pilot_report_fails_closed(tmp_path) -> None:
    path = tmp_path / "pilot.json"
    path.write_text(json.dumps({"schema_version": 2}), encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid Bluesky pilot"):
        load_pilot_report(path)
