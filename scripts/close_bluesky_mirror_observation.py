"""Close and archive Bluesky reliability work only after complete observation evidence."""

from __future__ import annotations

import argparse
from datetime import date, datetime
import json
from pathlib import Path
import re
import shutil
from typing import Any, Mapping


TRACK_ID = "bluesky_mirror_reliability_hardening_20260724"


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def validate_closeout(status: Mapping[str, Any], policy: Mapping[str, Any]) -> dict[str, Any]:
    required_dates = list(status.get("required_dates") or [])
    accepted_run_ids = list(status.get("accepted_run_ids") or [])
    expected_dates = []
    start = date.fromisoformat(str(policy["window_start"]))
    end = date.fromisoformat(str(policy["window_end"]))
    current = start
    while current <= end:
        expected_dates.append(current.isoformat())
        current = current.fromordinal(current.toordinal() + 1)
    evaluated_at = datetime.fromisoformat(str(status.get("evaluated_at")).replace("Z", "+00:00"))
    deadline_at = datetime.fromisoformat(str(policy["deadline_at"]).replace("Z", "+00:00"))
    positive_run_ids = all(isinstance(run_id, int) and run_id > 0 for run_id in accepted_run_ids)

    invariants = {
        "status_completed": status.get("status") == "completed",
        "complete": status.get("complete") is True,
        "window_elapsed": status.get("window_elapsed") is True,
        "evaluated_after_deadline": evaluated_at >= deadline_at,
        "dates_match_policy": required_dates == expected_dates,
        "all_dates_accepted": len(accepted_run_ids) == len(expected_dates),
        "positive_run_ids": positive_run_ids,
        "run_ids_unique": len(accepted_run_ids) == len(set(accepted_run_ids)),
        "no_missing_dates": status.get("missing_dates") == [],
        "no_rejected_receipts": status.get("rejected_receipts") == [],
        "expected_mirrors_match": status.get("expected_mirror_ids")
        == policy.get("expected_mirror_ids"),
        "deadline_matches": status.get("deadline_at") == policy.get("deadline_at"),
        "no_secret_values": status.get("secret_values_recorded") is False,
    }
    return {
        "schema_version": 1,
        "track_id": TRACK_ID,
        "ready": all(invariants.values()),
        "evaluated_at": status.get("evaluated_at"),
        "deadline_at": policy.get("deadline_at"),
        "required_dates": expected_dates,
        "accepted_run_ids": accepted_run_ids,
        "invariants": invariants,
        "posting_performed": False,
        "secret_values_recorded": False,
    }


def _replace_required(text: str, old: str, new: str, *, expected_count: int = 1) -> str:
    if text.count(old) != expected_count:
        raise ValueError(f"required closeout text count is not {expected_count}: {old}")
    return text.replace(old, new)


def apply_closeout(root: Path, report: Mapping[str, Any]) -> bool:
    active = root / "conductor" / "tracks" / TRACK_ID
    archived = root / "conductor" / "archive" / TRACK_ID
    if archived.exists() and not active.exists():
        metadata = _load_json(archived / "metadata.json")
        if metadata.get("status") != "completed":
            raise ValueError("existing archived track is not completed")
        return False
    if not active.is_dir():
        raise ValueError(f"active track not found: {active}")
    if archived.exists():
        raise ValueError(f"archive target already exists: {archived}")

    completed_at = str(report["evaluated_at"])[:10]
    metadata_path = active / "metadata.json"
    metadata = _load_json(metadata_path)
    metadata["status"] = "completed"
    metadata["github_issue_status"] = "closed"
    metadata["last_reconciled_at"] = completed_at
    metadata["completed_at"] = completed_at
    metadata["completion_summary"]["pending_actions"] = []
    metadata["observation_completion"] = {
        "deadline_at": report["deadline_at"],
        "evaluated_at": report["evaluated_at"],
        "required_dates": report["required_dates"],
        "accepted_run_ids": report["accepted_run_ids"],
        "secret_values_recorded": False,
        "posting_performed": False,
    }
    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )

    plan_path = active / "plan.md"
    plan = plan_path.read_text(encoding="utf-8")
    plan = _replace_required(
        plan,
        "- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md).",
        "- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md).",
        expected_count=2,
    )
    plan = _replace_required(
        plan,
        "- [ ] Task: Reconcile GitHub issue/subissue evidence.",
        "- [x] Task: Reconcile GitHub issue/subissue evidence.",
    )
    plan_path.write_text(plan, encoding="utf-8")

    runs = ", ".join(str(run_id) for run_id in report["accepted_run_ids"])
    review = f"""# Review Report: Bluesky Mirror Reliability Hardening

## Summary

Approved for archive. Implementation, cleanup, credential hygiene, and the
seven-day post-remediation observation gate are complete.

## Observation Evidence

- Required UTC dates: {report["required_dates"][0]} through {report["required_dates"][-1]}.
- Accepted scheduled run IDs: {runs}.
- Deadline: `{report["deadline_at"]}`.
- Evaluated at: `{report["evaluated_at"]}`.
- Missing dates: none.
- Rejected receipts: none.
- Posting performed during observation: no.
- Secret values recorded: no.

## Result

All fail-closed closeout invariants passed. The track is complete and archived.
"""
    (active / "review.md").write_text(review, encoding="utf-8")
    (active / "observation_closeout.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    tracks_path = root / "conductor" / "tracks.md"
    tracks = tracks_path.read_text(encoding="utf-8")
    updated, count = re.subn(
        r"\n## Bluesky Mirror Reliability Hardening \(2026-07-24\)\n.*?(?=\n## |\Z)",
        "",
        tracks,
        flags=re.DOTALL,
    )
    if count != 1:
        raise ValueError("active track registry entry was not found exactly once")
    tracks_path.write_text(updated.rstrip() + "\n", encoding="utf-8")

    archived.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(active), str(archived))
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument(
        "--status", type=Path, default=Path("conductor/bluesky_mirror_observation_status.json")
    )
    parser.add_argument(
        "--policy", type=Path, default=Path("conductor/bluesky_mirror_observation_policy.json")
    )
    parser.add_argument("--apply-if-ready", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    status_path = args.status if args.status.is_absolute() else root / args.status
    policy_path = args.policy if args.policy.is_absolute() else root / args.policy
    report = validate_closeout(_load_json(status_path), _load_json(policy_path))
    changed = False
    if args.apply_if_ready and report["ready"]:
        changed = apply_closeout(root, report)
    print(json.dumps({**report, "changed": changed}, sort_keys=True))


if __name__ == "__main__":
    main()
