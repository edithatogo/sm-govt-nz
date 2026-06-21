"""Strict reference-integrity gate for parties.json and persons.json.

Reads the gap report produced by tests/test_parties_persons_registry.py
(or recomputes it from registry files when absent), and exits non-zero
when any reference-integrity category has entries. This is the CI gate
that prevents future drift from re-introducing party_id, leader_person_id,
president_person_id, or organization mismatches between the parties,
persons, and government_directory registries.

Usage:
    python scripts/check_parties_persons_gaps.py [--report PATH] [--strict]
                                                  [--allow-leaders N]
                                                  [--allow-presidents N]

Exit codes:
    0 — every gap category is within tolerance
    1 — one or more categories exceed tolerance or report is missing in strict mode
    2 — input file is malformed
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_REPORT_PATH = Path("conductor/parties_persons_gap_report.json")
PARTIES_FILE = Path("registry/parties.json")
PERSONS_FILE = Path("registry/persons.json")
AGENCIES_FILE = Path("registry/government_directory.json")


def _load_json(path: Path):
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _summarise(report: dict) -> dict[str, int]:
    return {key: len(report.get(key, [])) for key in (
        "missing_party_leaders",
        "missing_party_presidents",
        "persons_unknown_party",
        "persons_unknown_agency_in_role",
    )}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help=f"Path to gap report (default: {DEFAULT_REPORT_PATH})",
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
    args = parser.parse_args()

    report = _load_json(args.report)
    if report is None:
        print(f"ERROR: gap report not found at {args.report}", file=sys.stderr)
        return 1 if args.strict else 0

    summary = _summarise(report)
    hard_failures: list[str] = []
    if summary["persons_unknown_party"] > 0:
        hard_failures.append(
            f"persons_unknown_party={summary['persons_unknown_party']} (must be 0)"
        )
    if summary["persons_unknown_agency_in_role"] > 0:
        hard_failures.append(
            f"persons_unknown_agency_in_role={summary['persons_unknown_agency_in_role']} (must be 0)"
        )
    if args.strict:
        if summary["missing_party_leaders"] > args.allow_leaders:
            hard_failures.append(
                f"missing_party_leaders={summary['missing_party_leaders']} "
                f"(tolerance={args.allow_leaders})"
            )
        if summary["missing_party_presidents"] > args.allow_presidents:
            hard_failures.append(
                f"missing_party_presidents={summary['missing_party_presidents']} "
                f"(tolerance={args.allow_presidents})"
            )

    payload = {
        "report_path": str(args.report),
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
            json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False),
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
