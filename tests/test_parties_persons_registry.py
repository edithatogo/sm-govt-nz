"""Schema, uniqueness, and reference-integrity tests for parties.json and persons.json.

Covers Phase 5 of the NZ Government Social Media Registry track:
- JSON Schema validation against registry/schema_parties.json and
  registry/schema_persons.json.
- Uniqueness of party_id and person_id values.
- Reference integrity gap report at
  conductor/parties_persons_gap_report.json.

The gap report is the authoritative artifact: it enumerates every
reference-integrity gap across the registry so downstream tooling and
implementer-2 can track alignment work. Tests in this module are
advisory — they verify the gap report structure and the data
schemas/uniqueness invariants that don't depend on OneDrive-synced file
hydration timing.

The strict CI gate for reference integrity lives in
.github/workflows/parties_persons_gap.yml and runs
scripts/check_parties_persons_gaps.py --strict. That script computes
the gap report from the registry files directly, which avoids the
pytest-internal file-read race conditions that occasionally surface on
OneDrive-synced Windows filesystems where different processes see
different file content for the same path.
"""

from __future__ import annotations

import json
from collections import Counter
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
CURRENT_MP_SOCIAL_REVIEW = Path(
    "conductor/current_mp_social_profile_review_20260623.json"
)

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
        for role in person.get("roles", []):
            org = role.get("organization")
            if org and org not in allowed_orgs:
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
    """Compute reference-integrity gaps and persist the report.

    This fixture records the current gap state and persists it to disk
    so the strict CI gate (parties_persons_gap.yml workflow) can act on
    it. The fixture is advisory — see the module docstring for the
    rationale and the strict gate location.
    """
    report = _build_reference_gap_report(parties, persons, agencies)
    GAP_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    GAP_REPORT_PATH.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
    return report


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


def test_check_parties_persons_gaps_script_exists():
    """The strict CI gate script must exist at scripts/check_parties_persons_gaps.py."""
    script = Path("scripts/check_parties_persons_gaps.py")
    assert script.exists()
    # Smoke test: --help should exit 0
    import subprocess
    result = subprocess.run(
        ["python", str(script), "--help"],
        capture_output=True, text=True
    )
    assert result.returncode == 0


def test_tenure_linked_profiles_reference_existing_roles(persons):
    """Every tenure-linked profile must point at a role on the same person."""
    missing = []
    for person in persons:
        role_ids = {
            role.get("role_id")
            for role in person.get("roles", [])
            if isinstance(role, dict)
        }
        for profile in person.get("tenure_linked_profiles", []):
            role_id = profile.get("role_id")
            if role_id not in role_ids:
                missing.append({"person_id": person["person_id"], "role_id": role_id})
    assert not missing, f"Tenure-linked profiles with unknown role_id: {missing}"


def test_representative_account_classification_sample(parties, persons, agencies):
    """The account-classification track keeps a narrow reviewed sample in data."""
    beehive = next(a for a in agencies if a["agency_id"] == "beehive-nz")
    national = next(p for p in parties if p["party_id"] == "national-party")
    luxon = next(p for p in persons if p["person_id"] == "christopher-luxon")
    campbell = next(p for p in persons if p["person_id"] == "hamish-campbell")

    assert beehive["social_profiles"]["bluesky"]["account_classification"] == "official"
    assert national["social_profiles"]["facebook"]["account_classification"] == "party"
    assert luxon["social_profiles"]["facebook"]["account_classification"] == "personal-public"
    assert campbell["social_profiles"]["facebook"]["account_classification"] == "campaign"

    office_profiles = [
        profile
        for profile in luxon.get("tenure_linked_profiles", [])
        if profile.get("account_classification") == "office"
    ]
    assert office_profiles
    assert office_profiles[0]["role_id"] == "prime-minister"
    assert office_profiles[0]["syndication_classification"] == "unique"


def test_all_social_profiles_have_account_classification(parties, persons, agencies):
    """Every seeded profile must carry account and syndication classifications."""
    missing = []

    for agency in agencies:
        for platform, profile in agency.get("social_profiles", {}).items():
            if "account_classification" not in profile or "syndication_classification" not in profile:
                missing.append({"record": agency["agency_id"], "platform": platform})

    for party in parties:
        for platform, profile in party.get("social_profiles", {}).items():
            if "account_classification" not in profile or "syndication_classification" not in profile:
                missing.append({"record": party["party_id"], "platform": platform})

    for person in persons:
        for platform, profile in person.get("social_profiles", {}).items():
            if "account_classification" not in profile or "syndication_classification" not in profile:
                missing.append({"record": person["person_id"], "platform": platform})
        for profile in person.get("tenure_linked_profiles", []):
            if "account_classification" not in profile or "syndication_classification" not in profile:
                missing.append(
                    {
                        "record": person["person_id"],
                        "platform": profile.get("platform"),
                        "role_id": profile.get("role_id"),
                    }
                )

    assert not missing, f"Profiles missing classification metadata: {missing}"




def _current_mp_records(persons):
    return [
        person
        for person in persons
        if any(
            role.get("category") == "mp" and role.get("is_current")
            for role in person.get("roles", [])
        )
    ]


def test_current_mp_roster_minimum_party_coverage(persons):
    """Current MP roster expansion must cover all major parliamentary parties."""
    expected_minimums = {
        "national-party": 49,
        "labour-party": 34,
        "green-party": 15,
        "act-new-zealand": 11,
        "new-zealand-first": 8,
        "te-pati-maori": 6,
    }
    counts = Counter(
        person.get("party_id") for person in _current_mp_records(persons)
    )
    shortfalls = {
        party_id: {"expected": expected, "actual": counts.get(party_id, 0)}
        for party_id, expected in expected_minimums.items()
        if counts.get(party_id, 0) < expected
    }
    assert not shortfalls, f"Current MP roster shortfalls: {shortfalls}"


def test_current_mp_roster_includes_replacement_mps(persons):
    """Recent list/electorate replacements must be represented as current MPs."""
    by_id = {person["person_id"]: person for person in persons}
    required_current = {
        "georgie-dansey",
        "dan-rosewarne",
        "oriini-kaipara",
        "david-wilson",
        "mike-davidson",
    }
    missing = []
    for person_id in required_current:
        person = by_id.get(person_id)
        if not person or person not in _current_mp_records(persons):
            missing.append(person_id)
    assert not missing, f"Replacement MPs missing current role: {missing}"

    peeni = by_id["peeni-henare"]
    current_peeni_mp_roles = [
        role
        for role in peeni.get("roles", [])
        if role.get("category") == "mp" and role.get("is_current")
    ]
    assert not current_peeni_mp_roles


def test_social_profile_handles_are_not_blank(persons):
    """Seeded social profile objects must not keep blank handles."""
    blank_handles = []
    for person in persons:
        for platform, profile in person.get("social_profiles", {}).items():
            if profile.get("handle") == "":
                blank_handles.append(
                    {"person_id": person["person_id"], "platform": platform}
                )
    assert not blank_handles, f"Blank social profile handles: {blank_handles}"


def test_current_mp_empty_social_profiles_are_reviewed(persons):
    """Current MPs with no structured social profile must be explicitly reviewed."""
    review = _load_json(CURRENT_MP_SOCIAL_REVIEW)
    assert review["captured_at"] == "2026-06-23"

    empty_current_profile_ids = {
        person["person_id"]
        for person in _current_mp_records(persons)
        if not person.get("social_profiles")
    }
    reviewed_ids = {
        item["person_id"] for item in review["reviewed_empty_profiles"]
    }
    assert reviewed_ids == empty_current_profile_ids
    assert review["reviewed_empty_profile_count"] == len(empty_current_profile_ids)



def test_recent_former_prime_ministers_are_seeded(persons):
    """Phase 7 seeds recent former Prime Ministers for historical continuity."""
    by_id = {person["person_id"]: person for person in persons}
    required = {
        "mike-moore",
        "jim-bolger",
        "jenny-shipley",
        "helen-clark",
        "john-key",
        "bill-english",
        "jacinda-ardern",
    }
    missing = required - set(by_id)
    assert not missing, f"Former Prime Ministers missing: {sorted(missing)}"

    for person_id in required:
        roles = by_id[person_id].get("roles", [])
        assert any(
            role.get("portfolio") == "Prime Minister"
            and role.get("organization") == "dpmc"
            and role.get("is_current") is False
            for role in roles
        ), f"{person_id} missing historical Prime Minister role"


def test_senior_judiciary_seed_includes_chief_justice(persons):
    """Phase 8 includes a verified senior judiciary seed record."""
    by_id = {person["person_id"]: person for person in persons}
    chief_justice = by_id["helen-winkelmann"]
    assert any(
        role.get("title") == "Chief Justice of New Zealand"
        and role.get("organization") == "courts-of-nz"
        and role.get("category") == "judge"
        and role.get("is_current")
        for role in chief_justice.get("roles", [])
    )


def test_current_public_sector_leaders_are_seeded(persons):
    """Phase 8 seeds current officeholders for core public-sector leader offices."""
    by_id = {person["person_id"]: person for person in persons}
    required = {
        "john-allen": ("office-of-the-ombudsman", "ombudsman"),
        "grant-taylor": ("office-of-the-auditor-general", "auditor-general"),
        "anna-breman": ("reserve-bank-of-nz", "reserve-bank-governor"),
        "richard-chambers": ("nz-police", "police-commissioner"),
        "tony-davies": ("nz-defence-force", "defence-chief"),
        "stephen-rainbow": ("human-rights-commission", "commissioner"),
        "claire-achmad": ("childrens-commissioner", "commissioner"),
        "ben-king": ("dpmc", "chief-executive"),
        "iain-rennie": ("the-treasury", "chief-executive"),
        "brian-roche": ("public-service-commission", "chief-executive"),
        "ellen-macgregor-reid": ("ministry-of-education", "chief-executive"),
    }

    missing = set(required) - set(by_id)
    assert not missing, f"Current public-sector leaders missing: {sorted(missing)}"

    for person_id, (organization, category) in required.items():
        assert any(
            role.get("organization") == organization
            and role.get("category") == category
            and role.get("is_current") is True
            for role in by_id[person_id].get("roles", [])
        ), f"{person_id} missing current {category} role for {organization}"


def test_superseded_public_sector_leaders_are_historical(persons):
    """Current-office refreshes must close superseded public-sector tenures."""
    by_id = {person["person_id"]: person for person in persons}
    for person_id, role_id in {
        "peter-boshier": "chief-ombudsman",
        "john-ryan": "auditor-general",
    }.items():
        roles = [
            role
            for role in by_id[person_id].get("roles", [])
            if role.get("role_id") == role_id
        ]
        assert roles
        assert roles[0].get("is_current") is False
        assert roles[0].get("end_date")


def test_historical_deputy_prime_ministers_are_seeded(persons):
    """Phase 7 includes former and current Deputy Prime Minister continuity."""
    by_id = {person["person_id"]: person for person in persons}
    required = {
        "don-mckinnon",
        "wyatt-creech",
        "jim-anderton",
        "michael-cullen",
        "bill-english",
        "paula-bennett",
        "winston-peters",
        "grant-robertson",
        "carmel-sepuloni",
        "david-seymour",
    }
    missing = required - set(by_id)
    assert not missing, f"Deputy Prime Ministers missing: {sorted(missing)}"

    for person_id in required:
        assert any(
            role.get("organization") == "dpmc"
            and role.get("portfolio") == "Deputy Prime Minister"
            for role in by_id[person_id].get("roles", [])
        ), f"{person_id} missing Deputy Prime Minister role"

    assert any(
        role.get("portfolio") == "Deputy Prime Minister"
        and role.get("is_current") is True
        for role in by_id["david-seymour"].get("roles", [])
    )


def test_major_historical_party_leaders_are_seeded(persons):
    """Phase 7 covers recent major-party leadership changes from 1990 onward."""
    by_id = {person["person_id"]: person for person in persons}
    required = {
        "mike-moore",
        "helen-clark",
        "phil-goff",
        "david-shearer",
        "david-cunliffe",
        "andrew-little",
        "jacinda-ardern",
        "jim-bolger",
        "jenny-shipley",
        "don-brash",
        "john-key",
        "bill-english",
        "simon-bridges",
        "todd-muller",
        "judith-collins",
    }
    missing = required - set(by_id)
    assert not missing, f"Major historical party leaders missing: {sorted(missing)}"

    for person_id in required:
        assert any(
            role.get("category") == "party-leader"
            and role.get("is_current") is False
            for role in by_id[person_id].get("roles", [])
        ), f"{person_id} missing historical party-leader role"


def test_canonical_role_organization_ids_are_seeded(agencies):
    """Quality gates protect common role organization IDs from regression."""
    agency_ids = {agency["agency_id"] for agency in agencies}
    assert {"the-treasury", "mbie", "nz-police"} <= agency_ids
