from pathlib import Path

from scripts.retry_fixable_archive_loop import retryable_source_ids, stable_shard


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
    assert "archive_completion_matrix.json" in script
    assert "archive_gap_map.json" in script
    assert 'cron: "23 17 * * *"' in workflow
    assert "api_endpoint,json_feed,website_page,linkedin" in workflow
    assert "--per-source-delay" in workflow
    assert "--retry-attempts" in workflow
    assert "--retry-backoff" in workflow
    assert "--discover-newsletters" in workflow
    assert "xvfb-run -a" in workflow
    assert "_archive_paced_retry_report.json" in script


def test_retryable_source_ids_selects_only_public_recovery_blockers() -> None:
    rows = [
        {
            "source_id": "linkedin-rate-limit",
            "source_type": "social_profile",
            "platform": "linkedin",
            "blocker_class": "linkedin_public_access_rate_limited",
        },
        {
            "source_id": "linkedin-auth",
            "platform": "linkedin",
            "blocker_class": "needs_authorized_seed_or_api",
        },
        {
            "source_id": "instagram-auth",
            "platform": "instagram",
            "blocker_class": "needs_authorized_seed_or_api",
        },
    ]
    shard_count = 8
    shard_index = stable_shard("linkedin-rate-limit", shard_count)

    selected = retryable_source_ids(
        {"sources": rows},
        "linkedin",
        shard_index=shard_index,
        shard_count=shard_count,
        limit=5,
    )

    assert selected == ["linkedin-rate-limit"]
