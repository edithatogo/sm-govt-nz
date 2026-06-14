import json
import pytest
from pathlib import Path
from jsonschema import validate, ValidationError

def load_schema():
    path = Path("registry/schema.json")
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
                # Parent might not be in this list if it's external or missing
                break
