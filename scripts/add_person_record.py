"""Append validated person records to registry/persons.json.

The input JSON may be either one person object or a list of person objects.
The command validates the resulting full registry against
registry/schema_persons.json before writing.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator


DEFAULT_REGISTRY_DIR = Path("registry")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def normalise_new_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        return [payload]
    if isinstance(payload, list) and all(isinstance(item, dict) for item in payload):
        return payload
    raise ValueError("input must be a person object or a list of person objects")


def duplicate_person_ids(records: list[dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    duplicates: list[str] = []
    for record in records:
        person_id = record.get("person_id")
        if not isinstance(person_id, str):
            continue
        if person_id in seen and person_id not in duplicates:
            duplicates.append(person_id)
        seen.add(person_id)
    return duplicates


def append_person_records(
    *,
    input_path: Path,
    registry_dir: Path = DEFAULT_REGISTRY_DIR,
    dry_run: bool = False,
    validate_only: bool = False,
) -> dict[str, Any]:
    persons_path = registry_dir / "persons.json"
    schema_path = registry_dir / "schema_persons.json"

    persons = load_json(persons_path)
    schema = load_json(schema_path)
    new_records = normalise_new_records(load_json(input_path))

    if not isinstance(persons, list):
        raise ValueError(f"{persons_path} must contain a list")

    incoming_duplicates = duplicate_person_ids(new_records)
    if incoming_duplicates:
        raise ValueError(
            "duplicate person_id values in input: " + ", ".join(incoming_duplicates)
        )

    existing_ids = {
        record.get("person_id")
        for record in persons
        if isinstance(record, dict) and isinstance(record.get("person_id"), str)
    }
    duplicate_existing = [
        record["person_id"]
        for record in new_records
        if isinstance(record.get("person_id"), str)
        and record["person_id"] in existing_ids
    ]
    if duplicate_existing:
        raise ValueError(
            "person_id values already exist: " + ", ".join(duplicate_existing)
        )

    updated = [*persons, *new_records]
    errors = sorted(
        Draft7Validator(schema).iter_errors(updated),
        key=lambda error: list(error.path),
    )
    if errors:
        formatted = "; ".join(
            f"{'/'.join(str(part) for part in error.path) or '<root>'}: {error.message}"
            for error in errors[:5]
        )
        raise ValueError(f"schema validation failed: {formatted}")

    if not dry_run and not validate_only:
        write_json(persons_path, updated)

    return {
        "input_count": len(new_records),
        "existing_count": len(persons),
        "result_count": len(updated),
        "wrote": not dry_run and not validate_only,
        "persons_path": str(persons_path),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        required=True,
        help="JSON file containing one person object or a list of person objects.",
    )
    parser.add_argument(
        "--registry-dir",
        type=Path,
        default=DEFAULT_REGISTRY_DIR,
        help="Registry directory containing persons.json and schema_persons.json.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and report counts without writing persons.json.",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Alias for --dry-run intended for validation gates.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        result = append_person_records(
            input_path=args.input,
            registry_dir=args.registry_dir,
            dry_run=args.dry_run,
            validate_only=args.validate_only,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
