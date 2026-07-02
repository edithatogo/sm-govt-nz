from pathlib import Path


def test_manual_seed_onboarding_workflow_builds_and_commits_report() -> None:
    workflow = Path(".github/workflows/manual_seed_onboarding.yml").read_text(encoding="utf-8")

    assert "scripts/build_manual_seed_onboarding_report.py" in workflow
    assert "facebook,instagram,threads,linkedin,x,newsletter" in workflow
    assert "conductor/manual_seed_onboarding_report.json" in workflow
    assert "conductor/manual_seed_onboarding_summary.md" in workflow
    assert "conductor/manual_seed_work_queue.json" in workflow
    assert "scripts/commit_state_updates.py" in workflow
    assert "manual_archive_seeds" not in workflow
