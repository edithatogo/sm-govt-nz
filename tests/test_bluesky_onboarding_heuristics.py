import json

from src.bluesky_onboarding_heuristics import choose_plan, default_state, rank_candidates, record_event, save_state


def test_plan_is_deterministic_without_history() -> None:
    assert choose_plan(default_state()).name == "headed_uc_cdp"


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
