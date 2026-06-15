"""
Verify that the compiled SQLite registry DB matches the source JSON.

Reads:
  - registry/government_directory.json
  - registry/government_directory.db

Validates:
  - Both files exist and are readable
  - Table structure (agencies, social_profiles)
  - Row counts match between JSON entries and DB rows
  - Every JSON agency has a corresponding DB row with matching fields
  - Every JSON social profile has a corresponding DB row
  - No orphaned rows in the DB

Outputs structured JSON report to stdout (and optionally a file).
"""

import argparse
import json
import os
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class Mismatch:
    """A single validation discrepancy."""

    field: str
    expected: Any
    actual: Any
    detail: str = ""


@dataclass
class RegistryValidation:
    json_path: str
    db_path: str
    json_exists: bool = False
    db_exists: bool = False
    json_entry_count: int = 0
    db_agency_count: int = 0
    db_profile_count: int = 0
    json_profile_count: int = 0
    tables_ok: bool = False
    row_counts_match: bool = False
    all_agencies_match: bool = False
    all_profiles_match: bool = False
    no_orphaned_rows: bool = False
    mismatches: list[Mismatch] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return (
            self.json_exists
            and self.db_exists
            and self.tables_ok
            and self.row_counts_match
            and self.all_agencies_match
            and self.all_profiles_match
            and self.no_orphaned_rows
        )

    @property
    def status(self) -> str:
        if not self.json_exists:
            return "json_missing"
        if not self.db_exists:
            return "db_missing"
        if not self.tables_ok:
            return "tables_missing"
        if not self.row_counts_match:
            return "row_count_mismatch"
        if not self.all_agencies_match or not self.all_profiles_match:
            return "field_mismatch"
        if not self.no_orphaned_rows:
            return "orphaned_rows"
        return "ok"

    def to_json(self) -> dict:
        return {
            "status": self.status,
            "ok": self.ok,
            "json_path": self.json_path,
            "db_path": self.db_path,
            "json_exists": self.json_exists,
            "db_exists": self.db_exists,
            "json_entry_count": self.json_entry_count,
            "db_agency_count": self.db_agency_count,
            "db_profile_count": self.db_profile_count,
            "json_profile_count": self.json_profile_count,
            "tables_ok": self.tables_ok,
            "row_counts_match": self.row_counts_match,
            "all_agencies_match": self.all_agencies_match,
            "all_profiles_match": self.all_profiles_match,
            "no_orphaned_rows": self.no_orphaned_rows,
            "mismatches": [
                {"field": m.field, "expected": m.expected, "actual": m.actual, "detail": m.detail}
                for m in self.mismatches
            ],
        }



def verify_registry(
    json_path: str = "registry/government_directory.json",
    db_path: str = "registry/government_directory.db",
) -> RegistryValidation:
    result = RegistryValidation(json_path=json_path, db_path=db_path)

    # --- Check files exist ---------------------------------------------------
    json_file = Path(json_path)
    db_file = Path(db_path)

    result.json_exists = json_file.exists()
    if not result.json_exists:
        return result

    result.db_exists = db_file.exists()
    if not result.db_exists:
        return result

    # --- Load JSON -----------------------------------------------------------
    with json_file.open("r", encoding="utf-8") as f:
        data: list[dict] = json.load(f)
    result.json_entry_count = len(data)

    # --- Count profiles in JSON ----------------------------------------------
    json_profile_count = 0
    for item in data:
        json_profile_count += len(item.get("social_profiles", {}))
    result.json_profile_count = json_profile_count

    # --- Connect to DB -------------------------------------------------------
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # --- Check tables exist --------------------------------------------------
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row["name"] for row in cursor.fetchall()}
    if "agencies" not in tables or "social_profiles" not in tables:
        result.tables_ok = False
        result.mismatches.append(
            Mismatch(
                field="tables",
                expected={"agencies", "social_profiles"},
                actual=sorted(tables),
                detail=f"Missing tables: expected agencies,social_profiles, got {sorted(tables)}",
            )
        )
        conn.close()
        return result
    result.tables_ok = True

    # --- Count DB rows -------------------------------------------------------
    cursor.execute("SELECT count(*) FROM agencies")
    result.db_agency_count = cursor.fetchone()[0]
    cursor.execute("SELECT count(*) FROM social_profiles")
    result.db_profile_count = cursor.fetchone()[0]

    result.row_counts_match = (
        result.json_entry_count == result.db_agency_count
        and result.json_profile_count == result.db_profile_count
    )
    if not result.row_counts_match:
        result.mismatches.append(
            Mismatch(
                field="row_counts",
                expected=f"agencies={result.json_entry_count}, profiles={result.json_profile_count}",
                actual=f"agencies={result.db_agency_count}, profiles={result.db_profile_count}",
                detail="Row counts differ between JSON source and SQLite DB",
            )
        )

    # --- Validate each agency fields -----------------------------------------
    cursor.execute("SELECT * FROM agencies ORDER BY agency_id")
    db_agencies = {row["agency_id"]: dict(row) for row in cursor.fetchall()}

    for item in data:
        aid = item["agency_id"]
        if aid not in db_agencies:
            result.all_agencies_match = False
            result.mismatches.append(
                Mismatch(
                    field=f"agencies.{aid}",
                    expected="present",
                    actual="missing",
                    detail=f"Agency '{aid}' missing from DB",
                )
            )
            continue

        db_row = db_agencies[aid]
        for col in ("name", "type", "official_website", "status"):
            expected = item.get(col)
            actual = db_row.get(col)
            if expected != actual:
                result.all_agencies_match = False
                result.mismatches.append(
                    Mismatch(
                        field=f"agencies.{aid}.{col}",
                        expected=expected,
                        actual=actual,
                        detail=f"Agency '{aid}' field '{col}' mismatch",
                    )
                )
        # Check parent_agency_id
        expected_parent = item.get("parent_agency_id")
        actual_parent = db_row.get("parent_agency_id")
        if expected_parent != actual_parent:
            result.all_agencies_match = False
            result.mismatches.append(
                Mismatch(
                    field=f"agencies.{aid}.parent_agency_id",
                    expected=expected_parent,
                    actual=actual_parent,
                    detail=f"Agency '{aid}' parent_agency_id mismatch",
                )
            )
    # --- Validate each social profile ----------------------------------------
    if result.all_agencies_match is False and not any(
        m.field.startswith("agencies.") for m in result.mismatches
    ):
        result.all_agencies_match = True

    for item in data:
        aid = item["agency_id"]
        profiles = item.get("social_profiles", {})
        for platform, profile in profiles.items():
            cursor.execute(
                "SELECT * FROM social_profiles WHERE agency_id=? AND platform=?",
                (aid, platform),
            )
            db_row = cursor.fetchone()
            if db_row is None:
                result.all_profiles_match = False
                result.mismatches.append(
                    Mismatch(
                        field=f"profiles.{aid}.{platform}",
                        expected="present",
                        actual="missing",
                        detail=f"Profile '{platform}' for agency '{aid}' missing from DB",
                    )
                )
                continue
            db_row = dict(db_row)
            for col in ("handle", "url", "status"):
                expected = profile.get(col)
                actual = db_row.get(col)
                if expected != actual:
                    result.all_profiles_match = False
                    result.mismatches.append(
                        Mismatch(
                            field=f"profiles.{aid}.{platform}.{col}",
                            expected=expected,
                            actual=actual,
                            detail=f"Profile '{platform}' for '{aid}' field '{col}' mismatch",
                        )
                    )

    if not any(m.field.startswith("profiles.") for m in result.mismatches):
        result.all_profiles_match = True

    # --- Check for orphaned rows ---------------------------------------------
    json_agency_ids = {item["agency_id"] for item in data}
    cursor.execute("SELECT agency_id FROM agencies")
    db_agency_ids = {row["agency_id"] for row in cursor.fetchall()}
    orphaned = db_agency_ids - json_agency_ids
    if orphaned:
        result.no_orphaned_rows = False
        result.mismatches.append(
            Mismatch(
                field="orphaned_agencies",
                expected="no orphaned agencies",
                actual=sorted(orphaned),
                detail=f"DB contains agencies not in JSON: {sorted(orphaned)}",
            )
        )
    else:
        result.no_orphaned_rows = True

    conn.close()
    return result


def build_report(validation: RegistryValidation) -> dict:
    return {
        "tool": "verify_registry_compilation",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "validation": validation.to_json(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify compiled SQLite registry DB matches the source JSON."
    )
    parser.add_argument(
        "--json",
        default="registry/government_directory.json",
        help="Path to the source JSON file (default: registry/government_directory.json)",
    )
    parser.add_argument(
        "--db",
        default="registry/government_directory.db",
        help="Path to the compiled SQLite DB (default: registry/government_directory.db)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional file path to write the JSON report to",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.json):
        report = {
            "tool": "verify_registry_compilation",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "validation": {
                "status": "json_missing",
                "ok": False,
                "json_path": args.json,
                "db_path": args.db,
                "json_exists": False,
                "db_exists": os.path.isfile(args.db),
            },
        }
        print(json.dumps(report, indent=2))
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(json.dumps(report, indent=2))
        sys.exit(1)

    result = verify_registry(json_path=args.json, db_path=args.db)
    report = build_report(result)
    report_json = json.dumps(report, indent=2)
    print(report_json)

    if args.output:
        output_path = os.path.abspath(args.output)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_json)

    if not result.ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
