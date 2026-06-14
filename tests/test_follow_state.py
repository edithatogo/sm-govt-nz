import pytest

from scripts.check_follow_status import load_follow_state, save_follow_state


@pytest.fixture
def temp_follow_state(tmp_path, monkeypatch):
    """Fixture to use a temporary follow state file."""
    temp_file = tmp_path / "follow_sync_state.json"
    monkeypatch.setattr("scripts.check_follow_status.FOLLOW_STATE_PATH", str(temp_file))
    return temp_file


def test_load_follow_state_missing(temp_follow_state):
    """Test loading when file is missing."""
    state = load_follow_state()
    assert state == {"last_updated": None, "follows": []}


def test_save_and_load_follow_state(temp_follow_state):
    """Test saving and then loading the state."""
    results = [
        {
            "platform": "bluesky",
            "follower": "alice",
            "target": "bob",
            "target_did": "did:plc:bob",
            "status": "following",
            "evidence": "at://123",
        }
    ]
    save_follow_state(results)

    state = load_follow_state()
    assert state["last_updated"] is not None
    assert len(state["follows"]) == 1
    assert state["follows"][0]["follower"] == "alice"
    assert state["follows"][0]["target_did"] == "did:plc:bob"
    assert state["follows"][0]["status"] == "following"
    assert state["follows"][0]["evidence"] == "at://123"


def test_load_follow_state_invalid_json(temp_follow_state):
    """Test loading an invalid JSON file."""
    with open(temp_follow_state, "w", encoding="utf-8") as f:
        f.write("invalid json")

    state = load_follow_state()
    assert state == {"last_updated": None, "follows": []}
