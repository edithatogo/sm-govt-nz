"""Build the current non-posting Bluesky hosted-operation plan from evidence."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any, Mapping


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    return value if isinstance(value, dict) else {}


def build_hosted_plan(
    reliability: Mapping[str, Any],
    empty_matrix: Mapping[str, Any],
    recovery: Mapping[str, Any],
    credential: Mapping[str, Any],
    *,
    generated_at: str = "",
) -> dict[str, Any]:
    """Summarize hosted evidence without treating approval as execution."""
    preflight = reliability.get("hosted_preflight") or {}
    cleanup = reliability.get("hosted_cleanup") or {}
    rotation_verified = (
        credential.get("rotation_verification") == "verified"
        or credential.get("rotation_verified") is True
    )
    recovery_complete = bool(
        recovery.get("apply_requested") is True
        and recovery.get("resumed") is True
        and recovery.get("status") in {"completed", "recovered", "resumed"}
    )
    preflight_complete = bool(
        preflight.get("conclusion") == "success"
        and preflight.get("posted", 0) == 0
    )
    cleanup_complete = bool(
        cleanup.get("conclusion") == "success"
        and cleanup.get("findings_valid") is True
    )
    stages = [
        {
            "action": "historical_backfill_empty_matrix_proof",
            "run_id": empty_matrix.get("hosted_success_run"),
            "status": "completed" if empty_matrix.get("hosted_success_run") else "pending",
            "posting_performed": False,
        },
        {
            "action": "recovery_diagnostic",
            "mirror_id": recovery.get("mirror_id", "courts-of-nz"),
            "status": "completed" if recovery_complete else "pending",
            "apply_requested": recovery.get("apply_requested"),
            "resumed": recovery.get("resumed"),
            "posting_performed": False,
        },
        {
            "action": "credential_preflight",
            "run_id": preflight.get("run_id"),
            "status": "completed" if preflight_complete else "pending",
            "posting_performed": bool(preflight.get("posted", 0)),
        },
        {
            "action": "cleanup_reconciliation",
            "run_id": cleanup.get("run_id"),
            "status": "completed" if cleanup_complete else "pending",
            "findings_valid": cleanup.get("findings_valid"),
            "posting_performed": False,
            "reports_committed": cleanup.get("reports_committed", []),
        },
        {
            "action": "credential_rotation_and_revocation",
            "status": "completed" if rotation_verified else "external_action_required",
            "posting_performed": False,
            "instructions": credential.get("external_action", ""),
        },
    ]
    return {
        "schema_version": 2,
        "generated_at": generated_at or datetime.now(UTC).isoformat(),
        "repository": "edithatogo/sm-govt-nz",
        "global_invariants": {
            "live_posting_allowed": False,
            "live_posting_performed": bool(reliability.get("live_posting_performed")),
            "destructive_cleanup_allowed": False,
            "secret_values_in_artifacts": False,
            "external_mutations_require_separate_approval": True,
        },
        "summary": {
            "completed": sum(stage["status"] == "completed" for stage in stages),
            "external_action_required": sum(
                stage["status"] == "external_action_required" for stage in stages
            ),
            "pending": sum(stage["status"] == "pending" for stage in stages),
        },
        "stages": stages,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reliability",
        type=Path,
        default=Path("conductor/bluesky_mirror_reliability_status.json"),
    )
    parser.add_argument(
        "--empty-matrix",
        type=Path,
        default=Path(
            "conductor/archive/bluesky_mirror_empty_matrix_noop_20260727/metadata.json"
        ),
    )
    parser.add_argument(
        "--recovery",
        type=Path,
        default=Path("conductor/bluesky_mirror_recovery/courts-of-nz.json"),
    )
    parser.add_argument(
        "--credential",
        type=Path,
        default=Path(
            "conductor/tracks/bluesky_mirror_credential_hygiene_20260724/metadata.json"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("conductor/bluesky_mirror_hosted_dry_run_plan.json"),
    )
    args = parser.parse_args()
    plan = build_hosted_plan(
        _load(args.reliability),
        _load(args.empty_matrix),
        _load(args.recovery),
        _load(args.credential),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(plan, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(plan["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
