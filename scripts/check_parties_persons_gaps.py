"""Strict reference-integrity gate for parties.json and persons.json.

By default this command recomputes reference-integrity gaps from the
current registry files. That prevents a stale checked-in gap report from
hiding current registry drift. Use --use-report only when intentionally
reviewing a historical report artifact.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

DEFAULT_REPORT_PATH = Path("conductor/parties_persons_gap_report.json")
DEFAULT_REGISTRY_DIR = Path("registry")

GAP_KEYS = (
    "missing_party_leaders",
    "missing_party_presidents",
    "persons_unknown_party",
    "persons_unknown_agency_in_role",
)


def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _require_list(path: Path) -> list[dict[str, Any]]:
    payload = _load_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"{path} must contain a JSON array")
    if not all(isinstance(item, dict) for item in payload):
        raise ValueError(f"{path} must contain only JSON objects")
    return payload


def build_reference_gap_report(
    parties: list[dict[str, Any]],
    persons: list[dict[str, Any]],
    agencies: list[dict[str, Any]],
) -> dict[str, list[Any]]:
    """Return all party/person/role reference-integrity gaps."""
    party_ids = {p["party_id"] for p in parties if isinstance(p.get("party_id"), str)}
    person_ids = {p["person_id"] for p in persons if isinstance(p.get("person_id"), str)}
    agency_ids = {a["agency_id"] for a in agencies if isinstance(a.get("agency_id"), str)}
    allowed_orgs = agency_ids | party_ids

    missing_party_leaders = [
        p["party_id"]
        for p in parties
        if p.get("leader_person_id") and p["leader_person_id"] not in person_ids
    ]
    missing_party_presidents = [
        p["party_id"]
        for p in parties
        if p.get("president_person_id") and p["president_person_id"] not in person_ids
    ]
    persons_unknown_party = [
        p["person_id"]
        for p in persons
        if p.get("party_id") and p["party_id"] not in party_ids
    ]
    persons_unknown_agency_in_role = []
    for person in persons:
        person_id = person.get("person_id", "<unknown-person>")
        for role in person.get("roles", []):
            if not isinstance(role, dict):
                continue
            org = role.get("organization")
            if org and org not in allowed_orgs:
                persons_unknown_agency_in_role.append(
                    {"person_id": person_id, "organization": org}
                )

    return {
        "missing_party_leaders": missing_party_leaders,
        "missing_party_presidents": missing_party_presidents,
        "persons_unknown_party": persons_unknown_party,
        "persons_unknown_agency_in_role": persons_unknown_agency_in_role,
    }


def recompute_reference_gap_report(registry_dir: Path) -> dict[str, list[Any]]:
    parties = _require_list(registry_dir / "parties.json")
    persons = _require_list(registry_dir / "persons.json")
    agencies = _require_list(registry_dir / "government_directory.json")
    return build_reference_gap_report(parties, persons, agencies)


def _summarise(report: dict[str, Any]) -> dict[str, int]:
    return {key: len(report.get(key, [])) for key in GAP_KEYS}


def _hard_failures(
    summary: dict[str, int],
    *,
    strict: bool,
    allow_leaders: int,
    allow_presidents: int,
) -> list[str]:
    hard_failures: list[str] = []
    if summary["persons_unknown_party"] > 0:
        hard_failures.append(
            f"persons_unknown_party={summary['persons_unknown_party']} (must be 0)"
        )
    if summary["persons_unknown_agency_in_role"] > 0:
        hard_failures.append(
            "persons_unknown_agency_in_role="
            f"{summary['persons_unknown_agency_in_role']} (must be 0)"
        )
    if strict:
        if summary["missing_party_leaders"] > allow_leaders:
            hard_failures.append(
                f"missing_party_leaders={summary['missing_party_leaders']} "
                f"(tolerance={allow_leaders})"
            )
        if summary["missing_party_presidents"] > allow_presidents:
            hard_failures.append(
                f"missing_party_presidents={summary['missing_party_presidents']} "
                f"(tolerance={allow_presidents})"
            )
    return hard_failures


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help=f"Path to gap report artifact (default: {DEFAULT_REPORT_PATH})",
    )
    parser.add_argument(
        "--registry-dir",
        type=Path,
        default=DEFAULT_REGISTRY_DIR,
        help=f"Registry directory to recompute from (default: {DEFAULT_REGISTRY_DIR})",
    )
    parser.add_argument(
        "--use-report",
        action="store_true",
        help="Read --report instead of recomputing from current registry files.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat every gap as a hard failure (CI gate mode).",
    )
    parser.add_argument(
        "--allow-leaders",
        type=int,
        default=0,
        help="Tolerance for missing party leader_person_ids (default: 0).",
    )
    parser.add_argument(
        "--allow-presidents",
        type=int,
        default=0,
        help="Tolerance for missing party president_person_ids (default: 0).",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        help="Optional path to write a normalised JSON summary for downstream tooling.",
    )
    parser.add_argument(
        "--write-report",
        action="store_true",
        help="Write the recomputed gap report to --report.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.use_report:
        report = _load_json(args.report)
        if report is None:
            print(f"ERROR: gap report not found at {args.report}", file=sys.stderr)
            return 1 if args.strict else 0
        report_source = "report"
    else:
        try:
            report = recompute_reference_gap_report(args.registry_dir)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"ERROR: could not recompute gap report: {exc}", file=sys.stderr)
            return 2
        report_source = "recomputed"
        if args.write_report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(
                json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

    summary = _summarise(report)
    hard_failures = _hard_failures(
        summary,
        strict=args.strict,
        allow_leaders=args.allow_leaders,
        allow_presidents=args.allow_presidents,
    )

    payload = {
        "report_path": str(args.report),
        "report_source": report_source,
        "registry_dir": str(args.registry_dir),
        "summary": summary,
        "tolerances": {
            "missing_party_leaders": args.allow_leaders,
            "missing_party_presidents": args.allow_presidents,
        },
        "strict_mode": args.strict,
        "hard_failures": hard_failures,
        "complete": not hard_failures,
    }

    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(
            json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    print(json.dumps(payload, indent=2, sort_keys=True))

    if hard_failures:
        print(
            "\nFAIL: reference-integrity gate failed:\n  "
            + "\n  ".join(hard_failures)
            + "\nUpdate registry data or relax tolerances via --allow-leaders / --allow-presidents.",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
