"""Build fail-closed Bluesky candidate readiness and account packets."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.bluesky_handle_lifecycle import (
    candidate_handle_error,
    validate_abbreviation_registry,
)
from src.bluesky_mirror_programme import (
    evaluate_source_eligibility,
    load_archive_records,
    load_registry,
    slugify,
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _load(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _write(path: str | Path, value: Mapping[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_candidate_readiness_inventory(
    registry: Mapping[str, Any],
    archive_root: str | Path,
    *,
    generated_at: str = "",
) -> dict[str, Any]:
    candidates = {
        str(row["mirror_id"]): row
        for row in registry["mirrors"]
        if row.get("lifecycle_state") == "candidate" and not row.get("enabled")
    }
    state: dict[str, dict[str, Any]] = {
        mirror_id: {
            "scanned_records": 0,
            "accepted_contract_records": 0,
            "accepted_unusable_records": 0,
            "rejection_reason_counts": {},
            "fingerprints": set(),
        }
        for mirror_id in candidates
    }
    root = Path(archive_root)
    if root.exists():
        for shard in sorted(root.rglob("*.jsonl")):
            for line in shard.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                raw = json.loads(line)
                mirror_id = slugify(str(raw.get("agency_id") or ""))
                account = candidates.get(mirror_id)
                if account is None:
                    continue
                item = state[mirror_id]
                item["scanned_records"] += 1
                decision = evaluate_source_eligibility(account, raw)
                if not decision.eligible:
                    reasons = item["rejection_reason_counts"]
                    reasons[decision.reason] = reasons.get(decision.reason, 0) + 1
                    continue
                item["accepted_contract_records"] += 1
                content = str(
                    raw.get("content") or raw.get("text") or raw.get("title") or ""
                ).strip()
                record_id = str(raw.get("record_id") or raw.get("post_id") or "")
                if not record_id or not content:
                    item["accepted_unusable_records"] += 1
                    continue
                created_at = str(raw.get("original_created_at") or raw.get("created_at") or "")
                item["fingerprints"].add(
                    hashlib.sha256(
                        f"{mirror_id}\0{created_at[:10]}\0{content.casefold()}".encode()
                    ).hexdigest()
                )

    rows: list[dict[str, Any]] = []
    for mirror_id, account in sorted(candidates.items()):
        item = state[mirror_id]
        backlog = len(item["fingerprints"])
        scanned = int(item["scanned_records"])
        if backlog:
            disposition = "eligible_backlog"
        elif scanned:
            disposition = "no_current_eligible_records"
        else:
            disposition = "temporarily_empty"
        rows.append(
            {
                "mirror_id": mirror_id,
                "agency_name": str(account["agency_name"]),
                "issue_number": account.get("issue_number"),
                "environment": str(account["environment"]),
                "handle_candidates": list(account.get("handle_candidates") or []),
                "scanned_records": scanned,
                "accepted_contract_records": int(item["accepted_contract_records"]),
                "accepted_unusable_records": int(item["accepted_unusable_records"]),
                "rejected_records": scanned - int(item["accepted_contract_records"]),
                "rejection_reason_counts": dict(sorted(item["rejection_reason_counts"].items())),
                "eligible_backlog": backlog,
                "disposition": disposition,
                "terminal": False,
                "terminal_evidence": [],
            }
        )
    if len({row["mirror_id"] for row in rows}) != len(candidates):
        raise ValueError("candidate inventory must contain every candidate exactly once")
    return {
        "schema_version": 1,
        "generated_at": generated_at or _now(),
        "selection_policy": "eligible_backlog_ascending_then_mirror_id",
        "candidate_count": len(rows),
        "eligible_candidate_count": sum(row["eligible_backlog"] > 0 for row in rows),
        "zero_eligible_candidate_count": sum(row["eligible_backlog"] == 0 for row in rows),
        "truncated": 0,
        "candidates": rows,
    }


def build_account_packet(
    registry: Mapping[str, Any],
    inventory: Mapping[str, Any],
    abbreviation_registry: Mapping[str, Any],
    handle_readiness: Mapping[str, Any],
    environment_readiness: Mapping[str, Any],
    mirror_id: str,
    *,
    generated_at: str = "",
) -> dict[str, Any]:
    validate_abbreviation_registry(abbreviation_registry)
    account = next(
        (row for row in registry["mirrors"] if row.get("mirror_id") == mirror_id),
        None,
    )
    if account is None:
        raise ValueError(f"Unknown mirror_id: {mirror_id}")
    readiness = next(
        (row for row in inventory["candidates"] if row.get("mirror_id") == mirror_id),
        None,
    )
    if readiness is None:
        raise ValueError(f"Readiness inventory lacks {mirror_id}")
    abbreviation = next(
        (row for row in abbreviation_registry["entries"] if row.get("agency_id") == mirror_id),
        None,
    )
    candidates = list(account.get("handle_candidates") or [])
    probes = list(handle_readiness.get("probes") or [])
    probe_handles = [str(row.get("handle") or "") for row in probes]
    candidate_errors = {
        handle: error
        for handle in candidates
        if (error := candidate_handle_error(handle))
    }
    handles_ready = (
        probe_handles == candidates
        and bool(candidates)
        and not candidate_errors
        and all(row.get("state") == "unregistered" for row in probes)
    )
    branch_policy = environment_readiness.get("deployment_branch_policy") or {}
    environment_ready = bool(
        environment_readiness.get("exists") is True
        and environment_readiness.get("name") == account.get("environment")
        and environment_readiness.get("secrets_configured") is False
        and branch_policy.get("custom_branch_policies") is True
        and branch_policy.get("protected_branches") is False
        and environment_readiness.get("allowed_branches") == ["master"]
    )
    abbreviation_ready = bool(
        abbreviation
        and abbreviation.get("abbreviation_status") == "approved"
        and abbreviation.get("approved_handle") == candidates[0]
    )
    eligibility_ready = int(readiness.get("eligible_backlog", 0)) > 0
    pre_registration_ready = all(
        (handles_ready, environment_ready, abbreviation_ready, eligibility_ready)
    )
    packet = {
        "schema_version": 1,
        "generated_at": generated_at or _now(),
        "mirror_id": mirror_id,
        "issue_number": account.get("issue_number"),
        "status": (
            "operator_registration_required" if pre_registration_ready else "evidence_incomplete"
        ),
        "pre_registration_ready": pre_registration_ready,
        "identity": {
            "agency_id": account["agency_id"],
            "agency_name": account["agency_name"],
            "public_name": account["public_name"],
            "display_name": account["display_name"],
            "profile_disclosure": account["profile_disclosure"],
            "bot_label_required": True,
        },
        "handle": {
            "selected": candidates[0] if candidates else "",
            "candidates": candidates,
            "availability_evidence": probes,
            "validation_errors": candidate_errors,
            "approved_abbreviation": (
                abbreviation.get("organisation_abbreviation") if abbreviation else None
            ),
            "approval_evidence": (
                abbreviation.get("abbreviation_approval_evidence") if abbreviation else None
            ),
        },
        "environment": {
            "name": account["environment"],
            "exists": environment_readiness.get("exists") is True,
            "secrets_configured": environment_readiness.get("secrets_configured"),
            "deployment_branch_policy": branch_policy,
            "allowed_branches": environment_readiness.get("allowed_branches", []),
            "evidence_url": environment_readiness.get("evidence_url"),
        },
        "source_contract": {
            "source_ids": list(account.get("source_ids") or []),
            "source_platforms": list(account.get("source_platforms") or []),
            "source_urls": list(account.get("source_urls") or []),
            "scanned_records": readiness["scanned_records"],
            "accepted_contract_records": readiness["accepted_contract_records"],
            "rejected_records": readiness["rejected_records"],
            "rejection_reason_counts": readiness["rejection_reason_counts"],
            "eligible_backlog": readiness["eligible_backlog"],
        },
        "gates": {
            "abbreviation_approved": abbreviation_ready,
            "candidate_handles_unregistered": handles_ready,
            "empty_isolated_environment_exists": environment_ready,
            "eligible_backlog_present": eligibility_ready,
            "account_registered": False,
            "profile_configured": False,
            "app_password_configured": False,
            "non_posting_preflight_passed": False,
            "backfill_approved": False,
        },
        "operator_checkpoints": [
            "register the selected handle and complete platform challenges",
            "apply the archive display name, unofficial disclosure, and bot label",
            "create an app password and populate the isolated GitHub Environment",
            "run non-posting preflight and record the public DID",
            "obtain separate approval before any historical backfill or live posting",
        ],
        "posting_performed": False,
        "secret_values_recorded": False,
    }
    flattened = json.dumps(packet, sort_keys=True).casefold()
    if "@gmail.com" in flattened or "+bluesky" in flattened:
        raise ValueError("account packet contains a forbidden complete registration alias")
    return packet


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", default="config/mirror_accounts.json")
    parser.add_argument("--archive-root", default="historical_archive_normalized")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inventory_command = subparsers.add_parser("inventory")
    inventory_command.add_argument("--output", required=True)

    packet_command = subparsers.add_parser("packet")
    packet_command.add_argument(
        "--abbreviations", default="config/bluesky_mirror_abbreviations.json"
    )
    packet_command.add_argument("--handle-readiness", required=True)
    packet_command.add_argument("--environment-readiness", required=True)
    packet_command.add_argument("--inventory", required=True)
    packet_command.add_argument("--mirror-id", required=True)
    packet_command.add_argument("--eligibility-output", required=True)
    packet_command.add_argument("--output", required=True)
    args = parser.parse_args()

    registry = load_registry(args.registry)
    if args.command == "inventory":
        inventory = build_candidate_readiness_inventory(registry, args.archive_root)
        _write(args.output, inventory)
        print(
            json.dumps(
                {
                    "candidate_count": inventory["candidate_count"],
                    "eligible_candidate_count": inventory["eligible_candidate_count"],
                    "zero_eligible_candidate_count": inventory["zero_eligible_candidate_count"],
                },
                sort_keys=True,
            )
        )
        return

    inventory = _load(args.inventory)
    account = next(row for row in registry["mirrors"] if row.get("mirror_id") == args.mirror_id)
    load_archive_records(
        account,
        args.archive_root,
        eligibility_report_path=args.eligibility_output,
    )
    packet = build_account_packet(
        registry,
        inventory,
        _load(args.abbreviations),
        _load(args.handle_readiness),
        _load(args.environment_readiness),
        args.mirror_id,
    )
    _write(args.output, packet)
    print(
        json.dumps(
            {
                "mirror_id": args.mirror_id,
                "pre_registration_ready": packet["pre_registration_ready"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
