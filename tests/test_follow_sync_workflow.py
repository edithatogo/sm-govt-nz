from pathlib import Path


def test_follow_sync_workflow_uses_repo_python_setup_action() -> None:
    workflow = Path(".github/workflows/follow_sync.yml").read_text(encoding="utf-8")

    assert "./.github/actions/setup-python-uv" in workflow
    assert "requirements: requirements.txt" in workflow
    assert "contents: read" in workflow
    assert "scripts/commit_state_updates.py" in workflow
    assert "--path conductor/follow_sync_state.json" in workflow
    assert "uv pip install --system -r requirements.txt" not in workflow
    assert "astral-sh/setup-uv" not in workflow
