import json
import sqlite3

from scripts.compile_registry import compile_registry


def test_compile_registry_domain_files(tmp_path):
    input_path = "registry/government_directory.json"
    output_dir = tmp_path / "domains"
    db_path = tmp_path / "government_directory.db"
    compile_registry(input_path, output_dir, db_path)
    json_files = list(output_dir.glob("*.json"))
    assert len(json_files) > 0, "No domain JSON files were generated"
    with open(json_files[0], "r", encoding="utf-8") as f:
        data = json.load(f)
        assert isinstance(data, list)
        assert len(data) > 0
        assert "agency_id" in data[0]


def test_compile_registry_sqlite(tmp_path):
    db_path = tmp_path / "government_directory.db"
    compile_registry(
        "registry/government_directory.json",
        tmp_path / "domains",
        db_path,
    )
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    expected_tables = {
        "agencies",
        "social_profiles",
        "parties",
        "party_social_profiles",
        "persons",
        "person_roles",
        "person_social_profiles",
        "tenure_linked_profiles",
    }
    missing = expected_tables - tables
    assert not missing, f"Missing tables: {missing}"
    cursor.execute("SELECT count(*) FROM agencies")
    assert cursor.fetchone()[0] > 0, "Agencies table is empty"
    cursor.execute("SELECT count(*) FROM social_profiles")
    assert cursor.fetchone()[0] > 0, "Social profiles table is empty"
    conn.close()
