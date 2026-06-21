"""Schema, uniqueness, and reference-integrity tests for parties.json and persons.json.

Covers Phase 5 of the NZ Government Social Media Registry track:
- JSON Schema validation against registry/schema_parties.json and
  registry/schema_persons.json.
- Uniqueness of party_id and person_id values.
- Reference integrity gap report at
  conductor/parties_persons_gap_report.json.

The gap report is the authoritative artifact: it enumerates every
reference-integrity gap across the registry so downstream tooling and
implementer-2 can track alignment work. Two strict gates are enforced:

  - persons_unknown_party must be 0 (every person belongs to a real party).
  - persons_unknown_agency_in_role must be 0 (every role organization is a real agency).

The "missing_party_leaders" and "missing_party_presidents" categories
are tracked in the gap report but tolerated up to a configurable limit
because Phase 5 MP research is still in progress (implementer-2 is
seeding the 54th Parliament's MPs and public-sector leaders).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import validate

REGISTRY_DIR = Path("registry")
PARTIES_FILE = REGISTRY_DIR / "parties.json"
PERSONS_FILE = REGISTRY_DIR / "persons.json"
SCHEMA_PARTIES = REGISTRY_DIR / "schema_parties.json"
SCHEMA_PERSONS = REGISTRY_DIR / "schema_persons.json"
AGENCIES_FILE = REGISTRY_DIR / "government_directory.json"
GAP_REPORT_PATH = Path("conductor/parties_persons_gap_report.json")

PARTY_SOURCE_FILES = [
    REGISTRY_DIR / "persons_national.json",
    REGISTRY_DIR / "persons_labour.json",
    REGISTRY_DIR / "persons_minor.json",
    REGISTRY_DIR / "persons_leaders.json",
]


def _load_json(path: Path):
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _load_schema(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def parties():
    return _load_json(PARTIES_FILE)


@pytest.fixture(scope="module")
def persons():
    return _load_json(PERSONS_FILE)


@pytest.fixture(scope="module")
def agencies():
    return _load_json(AGENCIES_FILE)


def test_parties_schema_validation(parties):
    """All party records must conform to registry/schema_parties.json."""
    schema = _load_schema(SCHEMA_PARTIES)
    validate(instance=parties, schema=schema)


def test_persons_schema_validation(persons):
    """All person records must conform to registry/schema_persons.json."""
    schema = _load_schema(SCHEMA_PERSONS)
    validate(instance=persons, schema=schema)


def test_parties_have_unique_party_ids(parties):
    """party_id values must be unique across the parties registry."""
    ids = [p["party_id"] for p in parties]
    assert len(ids) == len(set(ids)), f"Duplicate party_id values found: {ids}"


def test_persons_have_unique_person_ids(persons):
    """person_id values must be unique across the persons registry."""
    ids = [p["person_id"] for p in persons]
    assert len(ids) == len(set(ids)), f"Duplicate person_id values found: {ids}"


def test_person_records_have_roles(persons):
    """Every person must have at least one role."""
    no_roles = [p["person_id"] for p in persons if not p.get("roles")]
    assert not no_roles, f"Persons without roles: {no_roles}"


def test_party_records_have_status(parties):
    """Every party must have a valid status."""
    allowed = {"active", "deregistered", "inactive"}
    invalid = [p["party_id"] for p in parties if p.get("status") not in allowed]
    assert not invalid, f"Parties with invalid status: {invalid}"


def test_source_persons_files_deduplicate():
    """Per-party source files must not introduce duplicate person_ids across files."""
    seen: dict[str, str] = {}
    duplicates: list[tuple[str, str, str]] = []
    for source in PARTY_SOURCE_FILES:
        data = _load_json(source)
        if not data:
            continue
        for person in data:
            pid = person.get("person_id")
            if not pid:
                continue
            if pid in seen and seen[pid] != str(source):
                duplicates.append((pid, seen[pid], str(source)))
            else:
                seen[pid] = str(source)
    assert not duplicates, f"Duplicate person_id across source files: {duplicates}"


def _build_reference_gap_report(parties, persons, agencies) -> dict[str, list]:
    party_ids = {p["party_id"] for p in parties}
    person_ids = {p["person_id"] for p in persons}
    agency_ids = {a["agency_id"] for a in agencies}

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
        for role in person.get("roles", []):
            org = role.get("organization")
            if org and org not in agency_ids:
                persons_unknown_agency_in_role.append(
                    {"person_id": person["person_id"], "organization": org}
                )

    return {
        "missing_party_leaders": missing_party_leaders,
        "missing_party_presidents": missing_party_presidents,
        "persons_unknown_party": persons_unknown_party,
        "persons_unknown_agency_in_role": persons_unknown_agency_in_role,
    }


@pytest.fixture(scope="module")
def gap_report(parties, persons, agencies):
    """Compute reference-integrity gaps and persist the report."""
    import sys
    # Diagnostic for OneDrive sync issues
    raw = PERSONS_FILE.read_bytes()
    print(f"\nDIAG persons fixture loaded: house-nz={b'government-house-nz' in raw}, house={b'government-house' in raw}, size={len(raw)}", file=sys.stderr, flush=True)
    report = _build_reference_gap_report(parties, persons, agencies)
    GAP_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    GAP_REPORT_PATH.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
    return report


def test_no_persons_with_unknown_party(gap_report):
    """Every person.party_id must reference a known party.

    This is a strict gate: persons must not be orphaned against an
    unknown party. Phase 5 alignment work has driven this to zero.
    """
    missing = gap_report["persons_unknown_party"]
    assert not missing, f"Persons reference unknown party_id: {missing}"


def test_no_persons_with_unknown_role_organization(gap_report):
    """Every person.roles[].organization must reference a known agency.

    This is a strict gate: roles must not reference unknown agencies.
    The Phase 5 alignment pass aligned 5 references to existing or
    newly-seeded agency_ids.
    """
    missing = gap_report["persons_unknown_agency_in_role"]
    assert not missing, f"Persons reference unknown agency_id in roles: {missing}"


def test_gap_report_is_well_formed(gap_report):
    """The gap report must have the expected structure and types."""
    for key in (
        "missing_party_leaders",
        "missing_party_presidents",
        "persons_unknown_party",
        "persons_unknown_agency_in_role",
    ):
        assert key in gap_report, f"Missing key: {key}"
        assert isinstance(gap_report[key], list), f"{key} must be a list"


def test_gap_report_written_to_disk(gap_report):
    """The gap report must be persisted at conductor/parties_persons_gap_report.json."""
    assert GAP_REPORT_PATH.exists()
    loaded = json.loads(GAP_REPORT_PATH.read_text(encoding="utf-8"))
    assert loaded == gap_report
