import json
import pytest
from src.config import load_config, load_state, save_state, AppState, AppConfig

def test_load_config_success(tmp_path):
    config_data: AppConfig = {
        "monitored_accounts": [
            {
                "handle": "test.bsky.social",
                "did": "did:plc:123",
                "name": "Test Agency",
                "syndicate_to": ["x"]
            }
        ],
        "syndication_targets": {
            "x": {"enabled": True}
        }
    }
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config_data), encoding="utf-8")
    
    config = load_config(str(config_file))
    assert len(config["monitored_accounts"]) == 1
    assert config["monitored_accounts"][0]["handle"] == "test.bsky.social"
    assert config["syndication_targets"]["x"]["enabled"] is True

def test_load_config_missing_file():
    with pytest.raises(FileNotFoundError):
        load_config("nonexistent_config.json")

def test_load_config_invalid_schema(tmp_path):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"wrong_keys": []}), encoding="utf-8")
    
    with pytest.raises(ValueError, match="Invalid config.json"):
        load_config(str(config_file))

def test_load_state_default(tmp_path):
    # If the file does not exist, return an empty structure
    state = load_state(str(tmp_path / "nonexistent_state.json"))
    assert state == {"last_seen_post_ids": {}}

def test_save_and_load_state(tmp_path):
    state_file = tmp_path / "state.json"
    state_data: AppState = {
        "last_seen_post_ids": {
            "test.bsky.social": "12345"
        }
    }
    
    save_state(state_data, str(state_file))
    assert state_file.exists()
    
    loaded_state = load_state(str(state_file))
    assert loaded_state["last_seen_post_ids"]["test.bsky.social"] == "12345"
