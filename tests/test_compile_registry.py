import json
import sqlite3
from pathlib import Path

from scripts.compile_registry import compile_registry

def test_compile_registry_domain_files():
    # Setup test paths
    input_path = "registry/government_directory.json"
    output_dir = "registry/domains"
    db_path = "registry/government_directory.db"
    
    # Run compilation
    compile_registry(input_path, output_dir, db_path)
    
    # Verify domain files exist
    output_path = Path(output_dir)
    json_files = list(output_path.glob("*.json"))
    assert len(json_files) > 0, "No domain JSON files were generated"
    
    # Check one file content
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
    
    # Check tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='agencies'")
    assert cursor.fetchone() is not None, "Table 'agencies' missing"
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='social_profiles'")
    assert cursor.fetchone() is not None, "Table 'social_profiles' missing"
    
    # Check data integrity
    cursor.execute("SELECT count(*) FROM agencies")
    agency_count = cursor.fetchone()[0]
    assert agency_count > 0, "Agencies table is empty"
    
    cursor.execute("SELECT count(*) FROM social_profiles")
    profile_count = cursor.fetchone()[0]
    assert profile_count > 0, "Social profiles table is empty"
    
    conn.close()
