import json
import sqlite3
from pathlib import Path

from scripts.compile_registry import compile_registry


def test_compile_registry_domain_files():
    input_path = "registry/government_directory.json"
    output_dir = "registry/domains"
    db_path = "registry/government_directory.db"
    compile_registry(input_path, output_dir, db_path)
    output_path = Path(output_dir)
    json_files = list(output_path.glob("*.json"))
    assert len(json_files) > 0, "No domain JSON files were generated"
    with open(json_files[0], "r", encoding="utf-8") as f:
        data = json.load(f)
        assert isinstance(data, list)
        assert len(data) > 0
        assert "agency_id" in data[0]


def test_compile_registry_sqlite():
    db_path = "registry/government_directory.db"
    assert Path(db_path).exists(), "SQLite database was not generated"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    expected_tables = {
        "agencies", "social_profiles",
        "parties", "party_social_profiles",
        "persons", "person_roles", "person_social_profiles",
        "tenure_linked_profiles"
    }
    missing = expected_tables - tables
    assert not missing, f"Missing tables: {missing}"
    cursor.execute("SELECT count(*) FROM agencies")
    assert cursor.fetchone()[0] > 0, "Agencies table is empty"
    cursor.execute("SELECT count(*) FROM social_profiles")
    assert cursor.fetchone()[0] > 0, "Social profiles table is empty"
    conn.close()
