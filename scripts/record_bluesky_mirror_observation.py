"""Record and evaluate secret-free Bluesky mirror observation evidence."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
import json
from pathlib import Path
from typing import Any, Iterable, Mapping


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _mirror_ids(selected_matrix: Mapping[str, Any]) -> list[str]:
    include = selected_matrix.get("include")
    if not isinstance(include, list):
        raise ValueError("selected matrix must contain an include list")
    mirror_ids = sorted(
        {
            item["mirror_id"]
            for item in include
            if isinstance(item, dict)
            and isinstance(item.get("mirror_id"), str)
            and item["mirror_id"] != "__no_eligible_mirror__"
        }
    )
    if not mirror_ids:
        raise ValueError("observation receipts require at least one active mirror")
    return mirror_ids


def build_receipt(
    selected_matrix: Mapping[str, Any],
    *,
    observed_at: str,
    repository: str,
    workflow: str,
    run_id: int,
    run_attempt: int,
    commit_sha: str,
) -> dict[str, Any]:
    timestamp = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        raise ValueError("observed_at must include a timezone")
    if run_id <= 0 or run_attempt <= 0:
        raise ValueError("run_id and run_attempt must be positive")
    return {
        "schema_version": 1,
        "observation_date": timestamp.date().isoformat(),
        "observed_at": timestamp.isoformat(),
        "repository": repository,
        "workflow": workflow,
        "run_id": run_id,
        "run_attempt": run_attempt,
        "commit_sha": commit_sha,
        "mirror_ids": _mirror_ids(selected_matrix),
        "public_health": "passed",
        "credential_health": "passed",
        "posting_performed": False,
        "secret_values_recorded": False,
    }


def _dates(start: date, end: date) -> list[str]:
    return [
        (start + timedelta(days=offset)).isoformat() for offset in range((end - start).days + 1)
    ]


def evaluate_receipts(
    policy: Mapping[str, Any],
    receipts: Iterable[Mapping[str, Any]],
    *,
    evaluated_at: str,
) -> dict[str, Any]:
    required_dates = _dates(
        date.fromisoformat(str(policy["window_start"])),
        date.fromisoformat(str(policy["window_end"])),
    )
    expected_mirrors = sorted(str(value) for value in policy["expected_mirror_ids"])
    accepted: dict[str, Mapping[str, Any]] = {}
    rejected: list[dict[str, Any]] = []
    ignored: list[dict[str, Any]] = []
    run_ids: set[int] = set()

    for receipt in receipts:
        observation_date = receipt.get("observation_date")
        run_id = receipt.get("run_id")
        if observation_date not in required_dates:
            ignored.append({"observation_date": observation_date, "run_id": run_id})
            continue
        reasons: list[str] = []
        if receipt.get("mirror_ids") != expected_mirrors:
            reasons.append("mirror_set_mismatch")
        if receipt.get("public_health") != "passed":
            reasons.append("public_health_not_passed")
        if receipt.get("credential_health") != "passed":
            reasons.append("credential_health_not_passed")
        if receipt.get("posting_performed") is not False:
            reasons.append("posting_invariant_failed")
        if receipt.get("secret_values_recorded") is not False:
            reasons.append("secret_invariant_failed")
        if not isinstance(run_id, int) or run_id <= 0:
            reasons.append("invalid_run_id")
        elif run_id in run_ids:
            reasons.append("duplicate_run_id")
        if observation_date in accepted:
            reasons.append("duplicate_observation_date")
        if reasons:
            rejected.append(
                {"observation_date": observation_date, "run_id": run_id, "reasons": reasons}
            )
            continue
        accepted[str(observation_date)] = receipt
        run_ids.add(run_id)

    missing_dates = [value for value in required_dates if value not in accepted]
    evaluated_timestamp = datetime.fromisoformat(evaluated_at.replace("Z", "+00:00"))
    deadline = datetime.fromisoformat(str(policy["deadline_at"]).replace("Z", "+00:00"))
    window_elapsed = evaluated_timestamp >= deadline
    complete = not missing_dates and not rejected and window_elapsed
    return {
        "schema_version": 1,
        "evaluated_at": evaluated_at,
        "status": "completed" if complete else "observation_in_progress",
        "complete": complete,
        "window_start": policy["window_start"],
        "window_end": policy["window_end"],
        "window_elapsed": window_elapsed,
        "expected_mirror_ids": expected_mirrors,
        "deadline_at": policy["deadline_at"],
        "day_zero_anchor_run_ids": policy["day_zero_anchor_run_ids"],
        "required_dates": required_dates,
        "accepted_run_ids": [accepted[value]["run_id"] for value in sorted(accepted)],
        "missing_dates": missing_dates,
        "rejected_receipts": rejected,
        "ignored_receipts": ignored,
        "secret_values_recorded": False,
    }


def _write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    record = subparsers.add_parser("record")
    record.add_argument("--selected-matrix-json", required=True)
    record.add_argument("--observed-at", required=True)
    record.add_argument("--repository", required=True)
    record.add_argument("--workflow", required=True)
    record.add_argument("--run-id", required=True, type=int)
    record.add_argument("--run-attempt", required=True, type=int)
    record.add_argument("--commit-sha", required=True)
    record.add_argument("--output-dir", type=Path, required=True)
    evaluate = subparsers.add_parser("evaluate")
    evaluate.add_argument("--policy", type=Path, required=True)
    evaluate.add_argument("--receipts", type=Path, required=True)
    evaluate.add_argument("--evaluated-at", required=True)
    evaluate.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "record":
        receipt = build_receipt(
            json.loads(args.selected_matrix_json),
            observed_at=args.observed_at,
            repository=args.repository,
            workflow=args.workflow,
            run_id=args.run_id,
            run_attempt=args.run_attempt,
            commit_sha=args.commit_sha,
        )
        output = args.output_dir / f"{receipt['observation_date']}.json"
        _write(output, receipt)
        print(output)
        return
    policy = _load_json(args.policy)
    receipts = [_load_json(path) for path in sorted(args.receipts.glob("*.json"))]
    status = evaluate_receipts(policy, receipts, evaluated_at=args.evaluated_at)
    _write(args.output, status)
    print(json.dumps({"complete": status["complete"], "missing_dates": status["missing_dates"]}))


if __name__ == "__main__":
    main()
