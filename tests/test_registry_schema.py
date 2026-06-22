import json
import pytest
from pathlib import Path
from jsonschema import validate, ValidationError


REFRESH_VERIFICATION_STATUSES = [
    "current",
    "inactive",
    "deactivated",
    "historical",
    "unknown",
]


def load_schema(name="schema.json"):
    path = Path(f"registry/{name}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_registry_file_exists():
    path = Path("registry/government_directory.json")
    assert path.exists(), "registry/government_directory.json does not exist"


def test_registry_schema_valid():
    path = Path("registry/government_directory.json")
    if not path.exists():
        pytest.skip("Registry file not created yet")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    schema = load_schema()
    try:
        validate(instance=data, schema=schema)
    except ValidationError as e:
        pytest.fail(f"Schema validation failed: {e.message}")


def test_no_circular_dependencies():
    path = Path("registry/government_directory.json")
    if not path.exists():
        pytest.skip("Registry file not created yet")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    parent_map = {item["agency_id"]: item.get("parent_agency_id") for item in data}
    for agency_id in parent_map:
        visited = set()
        current = agency_id
        while current:
            if current in visited:
                pytest.fail(f"Circular dependency detected for agency: {agency_id}")
            visited.add(current)
            current = parent_map.get(current)
            if current and current not in parent_map:
                break


def test_parties_file_exists():
    path = Path("registry/parties.json")
    assert path.exists(), "registry/parties.json does not exist"


def test_parties_schema_valid():
    path = Path("registry/parties.json")
    if not path.exists():
        pytest.skip("Parties file not created yet")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    schema = load_schema("schema_parties.json")
    try:
        validate(instance=data, schema=schema)
    except ValidationError as e:
        pytest.fail(f"Parties schema validation failed: {e.message}")


def test_parties_have_required_fields():
    path = Path("registry/parties.json")
    if not path.exists():
        pytest.skip("Parties file not created yet")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    for party in data:
        assert "party_id" in party, "Party missing party_id"
        assert "name" in party, "Party missing name"
        assert "status" in party, "Party missing status"


def test_persons_file_exists():
    path = Path("registry/persons.json")
    assert path.exists(), "registry/persons.json does not exist"


def test_persons_schema_valid():
    path = Path("registry/persons.json")
    if not path.exists():
        pytest.skip("Persons file not created yet")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    schema = load_schema("schema_persons.json")
    try:
        validate(instance=data, schema=schema)
    except ValidationError as e:
        pytest.fail(f"Persons schema validation failed: {e.message}")


def test_persons_have_required_fields():
    path = Path("registry/persons.json")
    if not path.exists():
        pytest.skip("Persons file not created yet")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    for person in data:
        assert "person_id" in person, "Person missing person_id"
        assert "full_name" in person, "Person missing full_name"
        assert "roles" in person, "Person missing roles"
        assert len(person["roles"]) > 0, "Person has empty roles"


def test_persons_roles_valid():
    path = Path("registry/persons.json")
    if not path.exists():
        pytest.skip("Persons file not created yet")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    valid_categories = [
        "mp", "minister", "speaker", "governor-general",
        "commissioner", "chief-executive", "ombudsman",
        "auditor-general", "reserve-bank-governor",
        "police-commissioner", "defence-chief",
        "statutory-officer", "judge", "party-leader",
        "party-president", "mayor", "councillor",
        "local-government-ceo", "spokesperson", "shadow-minister",
        "deputy-leader", "deputy-shadow-leader", "opposition-leader"
    ]
    for person in data:
        for role in person.get("roles", []):
            assert "role_id" in role, "Role missing role_id"
            assert "title" in role, "Role missing title"
            assert "category" in role, "Role missing category"
            assert role["category"] in valid_categories,                 f"Invalid category '{role.get('category')}' for {person['person_id']}"
            assert "is_current" in role, "Role missing is_current"


def test_social_profile_refresh_metadata_valid():
    examples = [
        (
            "schema.json",
            [
                {
                    "agency_id": "example-agency",
                    "name": "Example Agency",
                    "type": "Department",
                    "official_website": "https://example.govt.nz",
                    "status": "active",
                    "social_profiles": {
                        "bluesky": {
                            "handle": "example.govt.nz",
                            "url": "https://bsky.app/profile/example.govt.nz",
                            "status": "active",
                            "last_checked_at": "2026-06-22",
                            "last_seen_at": "2026-06-22",
                            "verification_status": "current",
                        }
                    },
                }
            ],
        ),
        (
            "schema_parties.json",
            [
                {
                    "party_id": "example-party",
                    "name": "Example Party",
                    "status": "active",
                    "social_profiles": {
                        "facebook": {
                            "handle": "ExampleParty",
                            "url": "https://www.facebook.com/ExampleParty",
                            "status": "active",
                            "last_checked_at": "2026-06-22",
                            "last_seen_at": "2026-06-22",
                            "verification_status": "current",
                        }
                    },
                }
            ],
        ),
        (
            "schema_persons.json",
            [
                {
                    "person_id": "example-person",
                    "full_name": "Example Person",
                    "social_profiles": {
                        "x": {
                            "handle": "ExamplePerson",
                            "url": "https://x.com/ExamplePerson",
                            "status": "inactive",
                            "last_checked_at": "2026-06-22",
                            "last_seen_at": "2026-05-20",
                            "verification_status": "inactive",
                        }
                    },
                    "roles": [
                        {
                            "role_id": "example-role",
                            "title": "Former Member",
                            "organization": "nz-parliament",
                            "category": "mp",
                            "is_current": False,
                        }
                    ],
                }
            ],
        ),
    ]

    for schema_name, payload in examples:
        validate(instance=payload, schema=load_schema(schema_name))


@pytest.mark.parametrize("verification_status", REFRESH_VERIFICATION_STATUSES)
def test_social_profile_refresh_metadata_accepts_all_states(verification_status):
    examples = [
        (
            "schema.json",
            [
                {
                    "agency_id": "example-agency",
                    "name": "Example Agency",
                    "type": "Department",
                    "official_website": "https://example.govt.nz",
                    "status": "active",
                    "social_profiles": {
                        "bluesky": {
                            "handle": "example.govt.nz",
                            "url": "https://bsky.app/profile/example.govt.nz",
                            "status": "active",
                            "last_checked_at": "2026-06-22",
                            "last_seen_at": "2026-06-22",
                            "verification_status": verification_status,
                        }
                    },
                }
            ],
        ),
        (
            "schema_parties.json",
            [
                {
                    "party_id": "example-party",
                    "name": "Example Party",
                    "status": "active",
                    "social_profiles": {
                        "facebook": {
                            "handle": "ExampleParty",
                            "url": "https://www.facebook.com/ExampleParty",
                            "status": "active",
                            "last_checked_at": "2026-06-22",
                            "last_seen_at": "2026-06-22",
                            "verification_status": verification_status,
                        }
                    },
                }
            ],
        ),
        (
            "schema_persons.json",
            [
                {
                    "person_id": "example-person",
                    "full_name": "Example Person",
                    "social_profiles": {
                        "x": {
                            "handle": "ExamplePerson",
                            "url": "https://x.com/ExamplePerson",
                            "status": "inactive",
                            "last_checked_at": "2026-06-22",
                            "last_seen_at": "2026-05-20",
                            "verification_status": verification_status,
                        }
                    },
                    "tenure_linked_profiles": [
                        {
                            "platform": "x",
                            "handle": "ExamplePersonMP",
                            "url": "https://x.com/ExamplePersonMP",
                            "role_id": "example-role",
                            "last_checked_at": "2026-06-22",
                            "last_seen_at": "2026-05-20",
                            "verification_status": verification_status,
                        }
                    ],
                    "roles": [
                        {
                            "role_id": "example-role",
                            "title": "Former Member",
                            "organization": "nz-parliament",
                            "category": "mp",
                            "is_current": False,
                        }
                    ],
                }
            ],
        ),
    ]

    for schema_name, payload in examples:
        validate(instance=payload, schema=load_schema(schema_name))


def test_social_profile_refresh_metadata_optional():
    examples = [
        (
            "schema.json",
            [
                {
                    "agency_id": "example-agency",
                    "name": "Example Agency",
                    "type": "Department",
                    "official_website": "https://example.govt.nz",
                    "status": "active",
                    "social_profiles": {
                        "bluesky": {
                            "handle": "example.govt.nz",
                            "url": "https://bsky.app/profile/example.govt.nz",
                            "status": "active",
                        }
                    },
                }
            ],
        ),
        (
            "schema_parties.json",
            [
                {
                    "party_id": "example-party",
                    "name": "Example Party",
                    "status": "active",
                    "social_profiles": {
                        "facebook": {
                            "handle": "ExampleParty",
                            "url": "https://www.facebook.com/ExampleParty",
                            "status": "active",
                        }
                    },
                }
            ],
        ),
        (
            "schema_persons.json",
            [
                {
                    "person_id": "example-person",
                    "full_name": "Example Person",
                    "social_profiles": {
                        "x": {
                            "handle": "ExamplePerson",
                            "url": "https://x.com/ExamplePerson",
                            "status": "active",
                        }
                    },
                    "tenure_linked_profiles": [
                        {
                            "platform": "x",
                            "handle": "ExamplePersonMP",
                            "url": "https://x.com/ExamplePersonMP",
                            "role_id": "example-role",
                        }
                    ],
                    "roles": [
                        {
                            "role_id": "example-role",
                            "title": "Member",
                            "organization": "nz-parliament",
                            "category": "mp",
                            "is_current": True,
                        }
                    ],
                }
            ],
        ),
    ]

    for schema_name, payload in examples:
        validate(instance=payload, schema=load_schema(schema_name))


def test_social_profile_refresh_metadata_rejects_bad_status():
    payload = [
        {
            "agency_id": "example-agency",
            "name": "Example Agency",
            "type": "Department",
            "official_website": "https://example.govt.nz",
            "status": "active",
            "social_profiles": {
                "bluesky": {
                    "handle": "example.govt.nz",
                    "url": "https://bsky.app/profile/example.govt.nz",
                    "status": "active",
                    "last_checked_at": "2026-06-22",
                    "last_seen_at": "2026-06-22",
                    "verification_status": "fresh",
                }
            },
        }
    ]

    with pytest.raises(ValidationError):
        validate(instance=payload, schema=load_schema("schema.json"))


def test_social_profile_refresh_metadata_rejects_bad_date():
    payload = [
        {
            "person_id": "example-person",
            "full_name": "Example Person",
            "social_profiles": {
                "x": {
                    "handle": "ExamplePerson",
                    "url": "https://x.com/ExamplePerson",
                    "status": "active",
                    "last_checked_at": "2026-6-22",
                    "verification_status": "current",
                }
            },
            "roles": [
                {
                    "role_id": "example-role",
                    "title": "Member",
                    "organization": "nz-parliament",
                    "category": "mp",
                    "is_current": True,
                }
            ],
        }
    ]

    with pytest.raises(ValidationError):
        validate(instance=payload, schema=load_schema("schema_persons.json"))


def test_tenure_linked_profile_refresh_metadata_rejects_bad_status():
    payload = [
        {
            "person_id": "example-person",
            "full_name": "Example Person",
            "tenure_linked_profiles": [
                {
                    "platform": "x",
                    "handle": "ExamplePersonMP",
                    "url": "https://x.com/ExamplePersonMP",
                    "role_id": "example-role",
                    "last_checked_at": "2026-06-22",
                    "last_seen_at": "2026-05-20",
                    "verification_status": "fresh",
                }
            ],
            "roles": [
                {
                    "role_id": "example-role",
                    "title": "Member",
                    "organization": "nz-parliament",
                    "category": "mp",
                    "is_current": True,
                }
            ],
        }
    ]

    with pytest.raises(ValidationError):
        validate(instance=payload, schema=load_schema("schema_persons.json"))
