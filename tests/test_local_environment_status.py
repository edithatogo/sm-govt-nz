import json
from pathlib import Path


def test_local_environment_status_records_user_owned_pyproject_change() -> None:
    status = json.loads(Path("conductor/local_environment_status_20260615.json").read_text())
    worktree_note = next(note for note in status["notes"] if note["area"] == "worktree")

    assert worktree_note["path"] == "pyproject.toml"
    assert worktree_note["status"] == "dirty_user_owned_change"
    assert "Do not stage" in worktree_note["handling"]


def test_local_environment_status_prefers_cmd_until_powershell_config_is_stable() -> None:
    status = json.loads(Path("conductor/local_environment_status_20260615.json").read_text())
    shell_note = next(note for note in status["notes"] if note["area"] == "shell")

    assert shell_note["status"] == "use_cmd_for_repo_checks"
    assert "cmd.exe" in shell_note["handling"]


def test_local_environment_status_records_disk_pressure_guard() -> None:
    status = json.loads(Path("conductor/local_environment_status_20260615.json").read_text())
    disk_note = next(note for note in status["notes"] if note["area"] == "disk")

    assert disk_note["status"] == "c_drive_pressure_mitigated"
    assert "scripts/check_local_disk_space.py" in disk_note["handling"]
