from pathlib import Path


def test_threads_workflows_write_dedicated_archive_report() -> None:
    manual = Path(".github/workflows/archive_threads_manual_seeds.yml").read_text(encoding="utf-8")
    scheduled = Path(".github/workflows/archive_threads_scheduled.yml").read_text(encoding="utf-8")

    assert "--report conductor/threads_archive_report.json" in manual
    assert "--report conductor/threads_archive_report.json" in scheduled
    assert "--path conductor/threads_archive_report.json" in manual
    assert "--path conductor/threads_archive_report.json" in scheduled
    assert "THREADS_API_CAPTURE_ENABLED" in scheduled


def test_seed_missing_is_report_only_for_threads_readiness() -> None:
    workflow = Path(".github/workflows/validate_threads_manual_seeds.yml").read_text(encoding="utf-8")

    assert 'if item.get("readiness") in {"seed_empty", "seed_invalid"}' in workflow
    assert 'if item.get("readiness") in {"seed_missing", "seed_empty", "seed_invalid"}' not in workflow
    assert "Missing seed files are tracked in conductor reports only" in workflow
    assert "coverage gap tracked automatically" in workflow
    assert "gh issue close" in workflow


def test_invalid_or_empty_threads_seeds_remain_issue_worthy() -> None:
    workflow = Path(".github/workflows/validate_threads_manual_seeds.yml").read_text(encoding="utf-8")

    assert "seed_invalid" in workflow
    assert "seed_empty" in workflow
    assert "archive-input-needed" in workflow
    assert "gh issue create" in workflow


def test_threads_scheduled_workflow_closes_api_blocker_when_not_actionable() -> None:
    workflow = Path(".github/workflows/archive_threads_scheduled.yml").read_text(encoding="utf-8")

    assert 'THREADS_API_CAPTURE_ENABLED: ${{ vars.THREADS_API_CAPTURE_ENABLED || \'false\' }}' in workflow
    assert 'if result.get("status") in {"threads_permission_error", "threads_api_error"}' in workflow
    assert "gh issue close" in workflow
    assert "Live public Threads API capture is disabled" in workflow
    assert "Manual seeds remain the active automated capture path" in workflow
