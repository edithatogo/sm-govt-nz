from pathlib import Path


def test_archive_replay_workflow_exposes_only_reviewed_batch_sizes() -> None:
    workflow = Path(".github/workflows/archive_replay.yml").read_text(
        encoding="utf-8"
    )

    assert 'description: "Maximum reviewed archive records to post"' in workflow
    assert '          - "5"' in workflow
    assert '          - "10"' in workflow
    assert '          - "20"' in workflow
    assert '          - "50"' not in workflow
    assert '          - "drain"' not in workflow
    assert "--drain" not in workflow
