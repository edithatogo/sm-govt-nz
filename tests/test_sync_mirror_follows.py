import json
from unittest.mock import MagicMock, patch

import pytest

from scripts.sync_mirror_follows import main


@pytest.fixture
def mock_follow_state(tmp_path, monkeypatch):
    state_file = tmp_path / "follow_sync_state.json"
    state = {
        "last_updated": "2026-06-14T00:00:00Z",
        "follows": [
            {
                "platform": "bluesky",
                "follower": "follower.bsky.social",
                "target": "target.bsky.social",
                "target_did": "did:plc:target",
                "status": "not_following",
            }
        ],
    }
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f)
    monkeypatch.setattr("scripts.sync_mirror_follows.FOLLOW_STATE_PATH", str(state_file))
    return state_file


def test_sync_dry_run(mock_follow_state, monkeypatch, capsys):
    monkeypatch.setenv("BLUESKY_MIRROR_HANDLE", "follower.bsky.social")
    monkeypatch.setattr("sys.argv", ["scripts/sync_mirror_follows.py", "--dry-run"])

    main()

    captured = capsys.readouterr()
    assert "Detected 1 missing follows on Bluesky" in captured.out
    assert "Missing follows from current account (follower.bsky.social): 1" in captured.out
    assert "Dry-run complete" in captured.out


@patch("scripts.sync_mirror_follows.urlopen")
def test_sync_execute(mock_urlopen, mock_follow_state, monkeypatch, capsys):
    monkeypatch.setenv("BLUESKY_MIRROR_HANDLE", "follower.bsky.social")
    monkeypatch.setenv("BLUESKY_MIRROR_APP_PASSWORD", "secret")
    monkeypatch.setattr("sys.argv", ["scripts/sync_mirror_follows.py", "--execute"])

    # Mock login response
    mock_login_resp = MagicMock()
    mock_login_resp.read.return_value = json.dumps(
        {"accessJwt": "fake_token", "did": "did:plc:follower", "handle": "follower.bsky.social"}
    ).encode("utf-8")
    mock_login_resp.__enter__.return_value = mock_login_resp

    # Mock follow response
    mock_follow_resp = MagicMock()
    mock_follow_resp.read.return_value = json.dumps(
        {"uri": "at://did:plc:follower/app.bsky.graph.follow/123", "cid": "abc"}
    ).encode("utf-8")
    mock_follow_resp.__enter__.return_value = mock_follow_resp

    mock_urlopen.side_effect = [mock_login_resp, mock_follow_resp]

    main()

    captured = capsys.readouterr()
    assert "Logging in as follower.bsky.social..." in captured.out
    assert "Following target.bsky.social (did:plc:target)..." in captured.out
    assert (
        "Successfully followed. URI: at://did:plc:follower/app.bsky.graph.follow/123"
        in captured.out
    )
