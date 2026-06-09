import json
import os

REGISTRY_PATH = "registry/agencies.json"

def test_registry_file_exists():
    assert os.path.exists(REGISTRY_PATH)

def test_registry_schema_valid():
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    assert isinstance(data, list)
    assert len(data) >= 5
    
    for agency in data:
        assert "agency_id" in agency
        assert "name" in agency
        assert "type" in agency
        assert "portfolio" in agency
        assert "official_website" in agency
        assert "status" in agency
        assert "social_profiles" in agency
        
        # Validate that website is a valid URL
        assert agency["official_website"].startswith("http")
        
        # Verify profiles have handle and url
        for platform, profile in agency["social_profiles"].items():
            assert "handle" in profile
            assert "url" in profile
            assert "status" in profile
            assert profile["url"].startswith("http")
