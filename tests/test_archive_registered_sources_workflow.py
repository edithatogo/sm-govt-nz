from pathlib import Path


def test_archive_registered_sources_dry_run_commits_only_report() -> None:
    workflow = Path(".github/workflows/archive_registered_sources.yml").read_text(encoding="utf-8")

    dry_run_block = workflow.split("- name: Commit archive report updates", 1)[1].split("- name: Commit archive capture reports", 1)[0]
    assert "inputs.dry_run == 'true'" in dry_run_block
    assert "conductor/govt_archive_registered_sources_report.json" in dry_run_block
    assert "dist/archive_manifest.json" not in dry_run_block
    assert "historical_archive_raw/**" not in dry_run_block


def test_archive_registered_sources_capture_commits_and_uploads_generated_artifacts() -> None:
    workflow = Path(".github/workflows/archive_registered_sources.yml").read_text(encoding="utf-8")

    capture_block = workflow.split("- name: Commit archive capture reports", 1)[1].split("- name: Commit archive payloads", 1)[0]
    assert "inputs.dry_run == 'false'" in capture_block
    assert "dist/archive_manifest.json" in capture_block
    assert "dist/archive_compaction_manifest.json" in capture_block
    assert "historical_archive_raw/**" not in capture_block
    assert "historical_archive_normalized/**" not in capture_block
    assert "dist/historical_archive.tar.gz" in workflow
    assert "--publish" in workflow


def test_archive_registered_sources_payload_commit_is_explicit() -> None:
    workflow = Path(".github/workflows/archive_registered_sources.yml").read_text(encoding="utf-8")

    payload_block = workflow.split("- name: Commit archive payloads", 1)[1].split("- name: Upload generated corpus bundle", 1)[0]
    assert "inputs.commit_payloads == 'true'" in payload_block
    assert "historical_archive_raw/**" in payload_block
    assert "historical_archive_normalized/**" in payload_block


def test_youtube_scheduled_workflow_uses_dedicated_report_and_limit() -> None:
    workflow = Path(".github/workflows/archive_youtube_scheduled.yml").read_text(encoding="utf-8")

    assert "--report conductor/youtube_archive_report.json" in workflow
    assert "--limit-sources \"$channel_limit\"" in workflow
    assert "Commit YouTube dry-run report" in workflow
    assert "--path conductor/youtube_archive_report.json" in workflow
    assert "--force" in workflow
    assert "historical_archive_raw/youtube/**" in workflow


def test_website_scheduled_workflow_uses_dedicated_report_and_limit() -> None:
    workflow = Path(".github/workflows/archive_website_scheduled.yml").read_text(encoding="utf-8")

    assert "--report conductor/website_archive_report.json" in workflow
    assert "--limit-sources \"$page_limit\"" in workflow
    assert "Commit website dry-run report" in workflow
    assert "--path conductor/website_archive_report.json" in workflow
    assert "--force" in workflow
    assert "historical_archive_raw/website/**" in workflow
