import json
import pytest
from pathlib import Path
from jsonschema import validate, ValidationError


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
