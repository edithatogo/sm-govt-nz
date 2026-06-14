import subprocess

import pytest

from scripts.check_noop_diff import assert_noop, changed_paths


def test_check_noop_diff_passes_when_tracked_path_is_unchanged(tmp_path) -> None:
    _init_repo(tmp_path)
    path = tmp_path / "archive" / "record.json"
    path.parent.mkdir()
    path.write_text('{"id": "1"}\n', encoding="utf-8")
    _git(tmp_path, "add", "archive/record.json")
    _git(tmp_path, "commit", "-m", "seed")

    assert changed_paths(["archive"], cwd=tmp_path) == []
    assert_noop(["archive"], cwd=tmp_path)


def test_check_noop_diff_reports_changed_tracked_path(tmp_path) -> None:
    _init_repo(tmp_path)
    path = tmp_path / "archive" / "record.json"
    path.parent.mkdir()
    path.write_text('{"id": "1"}\n', encoding="utf-8")
    _git(tmp_path, "add", "archive/record.json")
    _git(tmp_path, "commit", "-m", "seed")
    path.write_text('{"id": "1", "changed": true}\n', encoding="utf-8")

    assert changed_paths(["archive"], cwd=tmp_path) == ["archive/record.json"]
    with pytest.raises(RuntimeError, match="record.json"):
        assert_noop(["archive"], cwd=tmp_path)


def _init_repo(path) -> None:
    _git(path, "init")
    _git(path, "config", "user.email", "test@example.test")
    _git(path, "config", "user.name", "Test")


def _git(path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=path, check=True, capture_output=True, text=True)
