from copy import deepcopy
import json
from pathlib import Path

from scripts.close_bluesky_mirror_observation import TRACK_ID, apply_closeout, validate_closeout


POLICY = {
    "window_start": "2026-07-28",
    "window_end": "2026-08-03",
    "expected_mirror_ids": ["accident-compensation-corporation", "courts-of-nz"],
    "deadline_at": "2026-08-03T09:15:55+00:00",
}
DATES = [
    "2026-07-28",
    "2026-07-29",
    "2026-07-30",
    "2026-07-31",
    "2026-08-01",
    "2026-08-02",
    "2026-08-03",
]


def complete_status() -> dict:
    return {
        "status": "completed",
        "complete": True,
        "window_elapsed": True,
        "required_dates": DATES,
        "accepted_run_ids": list(range(100, 107)),
        "missing_dates": [],
        "rejected_receipts": [],
        "expected_mirror_ids": POLICY["expected_mirror_ids"],
        "deadline_at": POLICY["deadline_at"],
        "evaluated_at": "2026-08-03T10:50:00+00:00",
        "secret_values_recorded": False,
    }


def write_fixture(root: Path) -> None:
    track = root / "conductor" / "tracks" / TRACK_ID
    track.mkdir(parents=True)
    (track / "metadata.json").write_text(
        json.dumps(
            {
                "id": TRACK_ID,
                "status": "observation_in_progress",
                "github_issue_status": "published",
                "last_reconciled_at": "2026-07-27",
                "completion_summary": {"pending_actions": ["observe"]},
            }
        ),
        encoding="utf-8",
    )
    (track / "plan.md").write_text(
        "- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md).\n"
        "- [ ] Task: Reconcile GitHub issue/subissue evidence.\n"
        "- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md).\n",
        encoding="utf-8",
    )
    (track / "review.md").write_text("pending\n", encoding="utf-8")
    (root / "conductor" / "tracks.md").write_text(
        "# Project Tracks\n\n## Bluesky Mirror Reliability Hardening (2026-07-24)\n- [ ] active\n",
        encoding="utf-8",
    )


def test_closeout_validation_requires_every_invariant() -> None:
    assert validate_closeout(complete_status(), POLICY)["ready"] is True
    for key, value in (
        ("complete", False),
        ("window_elapsed", False),
        ("missing_dates", ["2026-08-03"]),
        ("rejected_receipts", [{"run_id": 106}]),
        ("secret_values_recorded", True),
    ):
        status = deepcopy(complete_status())
        status[key] = value
        assert validate_closeout(status, POLICY)["ready"] is False


def test_closeout_rejects_duplicate_or_missing_runs() -> None:
    duplicate = complete_status()
    duplicate["accepted_run_ids"][-1] = duplicate["accepted_run_ids"][0]
    assert validate_closeout(duplicate, POLICY)["ready"] is False
    missing = complete_status()
    missing["accepted_run_ids"].pop()
    assert validate_closeout(missing, POLICY)["ready"] is False
    nonpositive = complete_status()
    nonpositive["accepted_run_ids"][-1] = 0
    assert validate_closeout(nonpositive, POLICY)["ready"] is False
    premature = complete_status()
    premature["evaluated_at"] = "2026-08-03T09:00:00+00:00"
    assert validate_closeout(premature, POLICY)["ready"] is False


def test_apply_archives_track_and_is_idempotent(tmp_path: Path) -> None:
    write_fixture(tmp_path)
    report = validate_closeout(complete_status(), POLICY)
    assert apply_closeout(tmp_path, report) is True
    active = tmp_path / "conductor" / "tracks" / TRACK_ID
    archived = tmp_path / "conductor" / "archive" / TRACK_ID
    assert not active.exists()
    assert archived.is_dir()
    metadata = json.loads((archived / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["status"] == "completed"
    assert metadata["completion_summary"]["pending_actions"] == []
    assert metadata["observation_completion"]["accepted_run_ids"] == list(range(100, 107))
    assert "- [ ]" not in (archived / "plan.md").read_text(encoding="utf-8")
    assert "Approved for archive" in (archived / "review.md").read_text(encoding="utf-8")
    assert TRACK_ID not in (tmp_path / "conductor" / "tracks.md").read_text(encoding="utf-8")
    assert apply_closeout(tmp_path, report) is False
