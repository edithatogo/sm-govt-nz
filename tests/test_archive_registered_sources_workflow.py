from pathlib import Path

import argparse
import json

from scripts.archive_registered_sources import build_report, write_summary


def test_archive_registered_sources_dry_run_commits_only_report() -> None:
    workflow = Path(".github/workflows/archive_registered_sources.yml").read_text(encoding="utf-8")

    assert "          - json_feed" in workflow
    assert "          - social_profile" in workflow
    assert 'python-version: "3.14"' in workflow
    assert "inputs.source_type || 'scheduled'" in workflow
    assert "inputs.offset_sources || '0'" in workflow
    dry_run_block = workflow.split("- name: Commit archive report updates", 1)[1].split("- name: Commit archive capture reports", 1)[0]
    assert "inputs.dry_run == 'true'" in dry_run_block
    assert "conductor/govt_archive_registered_sources_report.json" in dry_run_block
    assert "conductor/govt_archive_registered_sources_summary.md" in dry_run_block
    assert "dist/archive_manifest.json" not in dry_run_block
    assert "historical_archive_raw/**" not in dry_run_block


def test_archive_registered_sources_capture_commits_and_uploads_generated_artifacts() -> None:
    workflow = Path(".github/workflows/archive_registered_sources.yml").read_text(encoding="utf-8")

    capture_block = workflow.split("- name: Commit archive capture reports", 1)[1].split("- name: Commit archive payloads", 1)[0]
    assert "inputs.dry_run == 'false'" in capture_block
    assert "dist/archive_manifest.json" in capture_block
    assert "dist/archive_compaction_manifest.json" in capture_block
    assert "--max-attempts 10" in capture_block
    assert "conductor/govt_archive_registered_sources_summary.md" in capture_block
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
    assert "--max-attempts 10" in payload_block


def test_youtube_scheduled_workflow_uses_dedicated_report_and_limit() -> None:
    workflow = Path(".github/workflows/archive_youtube_scheduled.yml").read_text(encoding="utf-8")

    assert "--report conductor/youtube_archive_report.json" in workflow
    assert "--limit-sources \"$channel_limit\"" in workflow
    assert "channel_limit=\"${CHANNEL_LIMIT:-50}\"" in workflow
    assert "args+=(--agency-id \"$AGENCY_ID\")" in workflow
    assert 'inputs.agency_id }}"' not in workflow
    assert "Commit YouTube dry-run report" in workflow
    assert "--path conductor/youtube_archive_report.json" in workflow
    assert "scripts/build_archive_failure_triage_report.py" in workflow
    assert "--path conductor/youtube_archive_failure_triage_report.json" in workflow
    assert "--force" in workflow
    assert "historical_archive_raw/youtube/**" in workflow


def test_website_scheduled_workflow_uses_dedicated_report_and_limit() -> None:
    workflow = Path(".github/workflows/archive_website_scheduled.yml").read_text(encoding="utf-8")

    assert "--report conductor/website_archive_report.json" in workflow
    assert "--limit-sources \"$page_limit\"" in workflow
    assert "page_limit=\"${PAGE_LIMIT:-50}\"" in workflow
    assert "args+=(--agency-id \"$AGENCY_ID\")" in workflow
    assert 'inputs.agency_id }}"' not in workflow
    assert "Commit website dry-run report" in workflow
    assert "--path conductor/website_archive_report.json" in workflow
    assert "scripts/build_archive_failure_triage_report.py" in workflow
    assert "--path conductor/website_archive_failure_triage_report.json" in workflow
    assert "--force" in workflow
    assert "historical_archive_raw/website/**" in workflow


def test_historical_backlog_workflow_fans_out_source_shards_and_hf_publish() -> None:
    workflow = Path(".github/workflows/archive_historical_backlog.yml").read_text(encoding="utf-8")

    assert "name: Archive Historical Backlog" in workflow
    assert "actions: write" in workflow
    assert "scripts/build_historical_backlog_matrix.py" in workflow
    assert "default: \"rss,json_feed,bluesky,youtube,website_page,threads,social_profile\"" in workflow
    assert "matrix: ${{ fromJson(needs.build-backlog-matrix.outputs.matrix) }}" in workflow
    assert "batch_count: ${{ steps.matrix.outputs.batch_count }}" in workflow
    assert "gh workflow run \"Archive Registered Sources\"" in workflow
    assert "-f limit_sources=\"$LIMIT\"" in workflow
    assert "-f offset_sources=\"$OFFSET\"" in workflow
    assert "-f commit_payloads=\"$COMMIT_PAYLOADS\"" in workflow
    assert "-f publish=false" in workflow
    assert "wait-for-backlog-shards" in workflow
    assert "--workflow \"Archive Registered Sources\"" in workflow
    assert "All dispatched backlog shard runs completed successfully." in workflow
    assert "gh workflow run \"Publish Archives\"" in workflow
    assert "-f publication_target=huggingface" in workflow
    assert "-f archive_release_version=\"${{ steps.release.outputs.version }}\"" in workflow


def test_registered_sources_report_writes_summary(tmp_path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "source_id": "rss-1",
                        "agency_id": "agency",
                        "agency_name": "Agency",
                        "platform": "rss",
                        "source_type": "rss_feed",
                        "url": "https://example.govt.nz/feed",
                        "archive_status": "ready",
                        "feasibility": "high",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    report = build_report(
        argparse.Namespace(
            manifest=manifest,
            source_type="rss",
            agency_id="",
            include_blocked=False,
            raw_root=tmp_path / "raw",
            normalized_root=tmp_path / "normalized",
            manual_seed_root=tmp_path / "manual_archive_seeds",
            fetch_timeout=30,
            retry_failed_from=None,
            offset_sources=0,
            limit_sources=0,
            dry_run=True,
            max_bluesky_pages=1,
            max_threads_posts=25,
        )
    )

    summary_path = tmp_path / "summary.md"
    write_summary(summary_path, report)
    summary = summary_path.read_text(encoding="utf-8")
    assert "Registered Sources Archive Summary" in summary
    assert "`selected_sources`: 1" in summary
    assert "`rss`: 1" in summary
