from datetime import UTC, datetime, timedelta

from scripts.record_bluesky_mirror_observation import build_receipt, evaluate_receipts

MIRRORS = ["accident-compensation-corporation", "courts-of-nz"]
POLICY = {
    "window_start": "2026-07-28",
    "window_end": "2026-08-03",
    "expected_mirror_ids": MIRRORS,
    "day_zero_anchor_run_ids": [30253109107, 30253111190],
    "deadline_at": "2026-08-03T09:15:55+00:00",
}


def receipt(day: int, run_id: int) -> dict:
    selected_matrix = {
        "include": [
            {"mirror_id": mirror_id, "environment": f"bluesky-mirror-{mirror_id}"}
            for mirror_id in reversed(MIRRORS)
        ]
    }
    return build_receipt(
        selected_matrix,
        observed_at=(datetime(2026, 7, 28, tzinfo=UTC) + timedelta(days=day)).isoformat(),
        repository="edithatogo/sm-govt-nz",
        workflow="Bluesky Mirror Health",
        run_id=run_id,
        run_attempt=1,
        commit_sha=f"{run_id:040d}",
    )


def test_receipt_is_sorted_and_secret_free() -> None:
    value = receipt(0, 100)
    assert value["mirror_ids"] == MIRRORS
    assert value["public_health"] == "passed"
    assert value["credential_health"] == "passed"
    assert value["posting_performed"] is False
    assert value["secret_values_recorded"] is False


def test_evaluator_requires_every_date_and_elapsed_window() -> None:
    receipts = [receipt(day, 100 + day) for day in range(7)]
    before_end = evaluate_receipts(POLICY, receipts, evaluated_at="2026-08-02T23:59:59+00:00")
    complete = evaluate_receipts(POLICY, receipts, evaluated_at="2026-08-03T10:50:00+00:00")
    assert before_end["complete"] is False
    assert before_end["window_elapsed"] is False
    assert complete["complete"] is True
    assert complete["missing_dates"] == []


def test_evaluator_fails_closed_for_bad_or_duplicate_evidence() -> None:
    receipts = [receipt(day, 100 + day) for day in range(7)]
    bad = dict(receipts[2])
    bad["credential_health"] = "failed"
    duplicate = dict(receipts[3])
    duplicate["run_id"] = receipts[0]["run_id"]
    status = evaluate_receipts(
        POLICY,
        [*receipts[:2], bad, *receipts[3:], duplicate],
        evaluated_at="2026-08-03T10:50:00+00:00",
    )
    assert status["complete"] is False
    assert "2026-07-30" in status["missing_dates"]
    assert status["rejected_receipts"]


def test_evaluator_ignores_receipts_outside_window() -> None:
    receipts = [receipt(day, 100 + day) for day in range(7)]
    future = receipt(7, 200)
    status = evaluate_receipts(
        POLICY, [*receipts, future], evaluated_at="2026-08-04T02:50:00+00:00"
    )
    assert status["complete"] is True
    assert status["ignored_receipts"] == [{"observation_date": "2026-08-04", "run_id": 200}]
