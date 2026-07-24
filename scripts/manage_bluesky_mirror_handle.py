from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.bluesky_handle_lifecycle import (
    DEFAULT_ABBREVIATION_REGISTRY,
    DEFAULT_MIRROR_REGISTRY,
    DEFAULT_RETIRED_HANDLE_REPORT,
    DEFAULT_STALE_LINK_REPORT,
    custom_domain_readiness_plan,
    load_json,
    migration_plan,
    retired_handle_report,
    stale_link_report,
    validate_abbreviation_registry,
    verify_handle_identity,
)


def _entry(rows: list[dict[str, Any]], agency_id: str) -> dict[str, Any]:
    return next(row for row in rows if row.get("agency_id") == agency_id)


def _mirror(rows: list[dict[str, Any]], mirror_id: str) -> dict[str, Any]:
    return next(row for row in rows if row.get("mirror_id") == mirror_id)


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage Bluesky mirror handle lifecycle.")
    parser.add_argument(
        "--abbreviations", type=Path, default=DEFAULT_ABBREVIATION_REGISTRY
    )
    parser.add_argument("--mirrors", type=Path, default=DEFAULT_MIRROR_REGISTRY)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("validate")

    verify = subparsers.add_parser("verify")
    verify.add_argument("--mirror-id", required=True)

    plan = subparsers.add_parser("plan")
    plan.add_argument("--mirror-id", required=True)
    plan.add_argument("--old-handle", required=True)

    stale = subparsers.add_parser("stale-links")
    stale.add_argument("--old-handle", action="append", required=True)
    stale.add_argument("--root", type=Path, default=Path("."))
    stale.add_argument("--output", type=Path, default=DEFAULT_STALE_LINK_REPORT)

    availability = subparsers.add_parser("availability")
    availability.add_argument("--handle", required=True)

    retired = subparsers.add_parser("monitor-retired")
    retired.add_argument("--output", type=Path, default=DEFAULT_RETIRED_HANDLE_REPORT)
    retired.add_argument("--fail-on-actionable", action="store_true")

    custom_domain = subparsers.add_parser("custom-domain-plan")
    custom_domain.add_argument("--agency-id", required=True)

    args = parser.parse_args()
    abbreviations = load_json(args.abbreviations)
    validate_abbreviation_registry(abbreviations)
    if args.command == "validate":
        print(json.dumps({"valid": True, "entries": len(abbreviations["entries"])}))
        return 0

    mirrors = load_json(args.mirrors)
    if args.command == "stale-links":
        report = stale_link_report(args.root, args.old_handle)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(json.dumps(report))
        return 0
    if args.command == "availability":
        from src.bluesky_handle_lifecycle import probe_handle

        result = probe_handle(args.handle)
        print(json.dumps(result, sort_keys=True))
        return 0 if result["state"] != "probe_failed" else 1
    if args.command == "monitor-retired":
        report = retired_handle_report(abbreviations)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(json.dumps(report, sort_keys=True))
        return 1 if args.fail_on_actionable and report["actionable_count"] else 0
    if args.command == "custom-domain-plan":
        print(
            json.dumps(
                custom_domain_readiness_plan(abbreviations, args.agency_id),
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    mirror = _mirror(mirrors["mirrors"], args.mirror_id)
    entry = _entry(abbreviations["entries"], mirror["agency_id"])
    if args.command == "verify":
        result = verify_handle_identity(entry["approved_handle"], entry["account_did"])
        print(json.dumps(result, sort_keys=True))
        return 0 if result["valid"] else 1
    if args.command == "plan":
        print(json.dumps(migration_plan(mirror, entry, old_handle=args.old_handle), indent=2))
        return 0
    raise AssertionError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
