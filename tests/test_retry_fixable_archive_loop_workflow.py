from pathlib import Path


def test_retry_fixable_archive_loop_workflow_wraps_bounded_loop_and_commit() -> None:
    workflow = Path(".github/workflows/retry_fixable_archive_loop.yml").read_text(encoding="utf-8")
    script = Path("scripts/retry_fixable_archive_loop.py").read_text(encoding="utf-8")

    assert "name: Retry Fixable Archive Loop" in workflow
    assert "scripts/retry_fixable_archive_loop.py" in workflow
    assert "max_iterations" in workflow
    assert "source_types" in workflow
    assert "commit_changes" in workflow
    assert "conductor/archive_gap_map.json" in workflow
    assert "conductor/govt_archive_registered_sources_report.json" in workflow
    assert "conductor/govt_archive_registered_sources_summary.md" in workflow
    assert "historical_archive_raw" in workflow
    assert "historical_archive_normalized" in workflow
    assert "git add -f historical_archive_raw historical_archive_normalized" in workflow
    assert "retry fixable backlog loop" in workflow
    assert "--retry-gap-map-from" in script
    assert "archive_gap_map.json" in script
