import json

import pytest

from src.archive_state import load_archive_state, save_archive_cursor


def test_load_archive_state_default(tmp_path):
    assert load_archive_state(tmp_path / "missing.json") == {"source_cursors": {}}


def test_save_archive_cursor_does_not_touch_syndication_state(tmp_path):
    archive_state = tmp_path / "archive_state.json"
    syndication_state = tmp_path / "state.json"
    syndication_state.write_text(
        json.dumps({"last_seen_post_ids": {"courtsofnz.bsky.social": "old"}}),
        encoding="utf-8",
    )

    saved = save_archive_cursor("courts-nz-rss-website", "rss-cursor", archive_state)

    assert saved["source_cursors"]["courts-nz-rss-website"] == "rss-cursor"
    assert json.loads(syndication_state.read_text(encoding="utf-8")) == {
        "last_seen_post_ids": {"courtsofnz.bsky.social": "old"}
    }


def test_load_archive_state_rejects_invalid_shape(tmp_path):
    archive_state = tmp_path / "archive_state.json"
    archive_state.write_text(json.dumps({"last_seen_post_ids": {}}), encoding="utf-8")

    with pytest.raises(ValueError, match="source_cursors"):
        load_archive_state(archive_state)
