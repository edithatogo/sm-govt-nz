from pathlib import Path

import argparse
import json

from scripts.archive_registered_sources import build_report, write_summary


def test_archive_registered_sources_dry_run_commits_only_report() -> None:
    workflow = Path(".github/workflows/archive_registered_sources.yml").read_text(encoding="utf-8")

    assert "          - json_feed" in workflow
    assert "          - social_profile" in workflow
    assert "          - newsletter" in workflow
    assert "./.github/actions/setup-python-uv" in workflow
    assert "requirements: requirements.txt" in workflow
    assert "          - feed" in workflow
    assert "          - browser_and_feed" in workflow
    assert "X_FEED_PROVIDERS" in workflow
    assert "RSSHUB_BASE_URLS" in workflow
    assert "NITTER_BASE_URLS" in workflow
    assert "X_AUTH_SCRAPE_ENABLED" in workflow
    assert "newsboat_health_check" in workflow
    assert "newsboat -u \"$urls\"" in workflow
    assert "conductor/x_feed_archive_report.json" in workflow
    assert "conductor/x_feed_archive_offset_${offset_sources}_report.json" in workflow
    assert "conductor/x_browser_and_feed_archive_offset_${offset_sources}_report.json" in workflow
    assert "--x-feed-providers" in workflow
    install_block = workflow.split("- name: Install browser runtime dependencies", 1)[1].split("- name: Install Newsboat for optional X feed health check", 1)[0]
    assert "inputs.capture_backend == 'browser'" in install_block
    assert "inputs.capture_backend == 'browser_and_feed'" in install_block
    assert "inputs.capture_backend == 'feed'" not in install_block
    assert "inputs.source_type || 'scheduled'" in workflow
    assert "inputs.offset_sources || '0'" in workflow
    assert "Resolve archive report paths" in workflow
    assert "ARCHIVE_REPORT_PATH=$report_path" in workflow
    assert "safe_agency_id" in workflow
    assert "${safe_source_type}_archive_${safe_agency_id}_report.json" in workflow
    assert "archive_offset_${offset_sources}_report.json" in workflow
    assert "--report \"$ARCHIVE_REPORT_PATH\"" in workflow
    assert "--summary \"$ARCHIVE_SUMMARY_PATH\"" in workflow
    dry_run_block = workflow.split("- name: Commit archive report updates", 1)[1].split("- name: Commit archive capture reports", 1)[0]
    assert "inputs.dry_run == 'true'" in dry_run_block
    assert '"$ARCHIVE_REPORT_PATH"' in dry_run_block
    assert '"$ARCHIVE_SUMMARY_PATH"' in dry_run_block
    assert "dist/archive_manifest.json" not in dry_run_block
    assert "historical_archive_raw/**" not in dry_run_block


def test_archive_registered_sources_capture_commits_and_uploads_generated_artifacts() -> None:
    workflow = Path(".github/workflows/archive_registered_sources.yml").read_text(encoding="utf-8")

    capture_block = workflow.split("- name: Commit archive capture reports", 1)[1].split("- name: Commit archive payloads", 1)[0]
    assert "inputs.dry_run == 'false'" in capture_block
    assert "scripts/build_archive_gap_map.py" in capture_block
    assert "--path conductor/archive_gap_map.json" in capture_block
    assert "dist/archive_manifest.json" in capture_block
    assert "dist/archive_compaction_manifest.json" in capture_block
    assert "--max-attempts 10" in capture_block
    assert '"$ARCHIVE_REPORT_PATH"' in capture_block
    assert '"$ARCHIVE_SUMMARY_PATH"' in capture_block
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
    assert "scripts/build_archive_gap_map.py" in workflow
    assert "--path conductor/youtube_archive_gap_map.json" in workflow
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
    assert "scripts/build_archive_gap_map.py" in workflow
    assert "--path conductor/website_archive_gap_map.json" in workflow
    assert "--force" in workflow
    assert "historical_archive_raw/website/**" in workflow


def test_historical_backlog_workflow_fans_out_source_shards_and_hf_publish() -> None:
    workflow = Path(".github/workflows/archive_historical_backlog.yml").read_text(encoding="utf-8")

    assert "name: Archive Historical Backlog" in workflow
    assert "actions: write" in workflow
    assert "scripts/build_historical_backlog_matrix.py" in workflow
    assert "default: \"rss,json_feed,api,bluesky,youtube,website_page,threads,x,linkedin,newsletter\"" in workflow
    assert "matrix: ${{ fromJson(needs.build-backlog-matrix.outputs.matrix) }}" in workflow
    assert "batch_count: ${{ steps.matrix.outputs.batch_count }}" in workflow
    assert "gh workflow run \"Archive Registered Sources\"" in workflow
    assert "-f limit_sources=\"$LIMIT\"" in workflow
    assert "-f offset_sources=\"$OFFSET\"" in workflow
    assert "-f commit_payloads=\"$COMMIT_PAYLOADS\"" in workflow
    assert "-f capture_backend=\"$capture_backend\"" in workflow
    assert "X_CAPTURE_BACKEND: ${{ inputs.x_capture_backend || 'feed' }}" in workflow
    assert "backend=$capture_backend" in workflow
    assert "-f publish=false" in workflow
    assert "wait-for-backlog-shards" in workflow
    assert "--workflow \"Archive Registered Sources\"" in workflow
    assert "All dispatched backlog shard runs completed successfully." in workflow
    assert "gh workflow run \"Publish Archives\"" in workflow
    assert "-f publication_target=\"${{ inputs.publication_target || 'all' }}\"" in workflow
    assert "-f archive_release_version=\"${{ steps.release.outputs.version }}\"" in workflow


def test_x_feed_scheduled_workflow_dispatches_feed_backend() -> None:
    workflow = Path(".github/workflows/archive_x_feed_scheduled.yml").read_text(encoding="utf-8")

    assert "name: Archive X Feed Scheduled" in workflow
    assert "actions: write" in workflow
    assert "gh workflow run \"Archive Registered Sources\"" in workflow
    assert "-f source_type=x" in workflow
    assert "-f capture_backend=feed" in workflow
    assert "-f publish=false" in workflow
    assert "cron: \"31 1 * * *\"" in workflow


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


def test_website_scheduled_workflow_preserves_browser_gap_supersession() -> None:
    workflow = Path(".github/workflows/archive_website_scheduled.yml").read_text(encoding="utf-8")

    assert "conductor/website_browser_archive_report.json" in workflow
    assert "--report conductor/website_browser_archive_report.json" in workflow
    assert "--output conductor/website_archive_gap_map.json" in workflow
