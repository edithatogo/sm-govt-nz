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
    assert "--rotation-index" in workflow
    assert "--discover-newsletters" in workflow
    assert "xvfb-run -a" in workflow
    assert "_archive_paced_retry_report.json" in script


def test_retryable_source_ids_selects_only_public_recovery_blockers() -> None:
    rows = [
        {
            "candidate_id": "manifest-linkedin-rate-limit",
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
    shard_index = stable_shard("manifest-linkedin-rate-limit", shard_count)

    selected = retryable_source_ids(
        {"sources": rows},
        "linkedin",
        shard_index=shard_index,
        shard_count=shard_count,
        limit=5,
    )

    assert selected == ["manifest-linkedin-rate-limit"]


def test_retryable_source_ids_rotates_over_shard_overflow() -> None:
    rows = [
        {
            "candidate_id": f"linkedin-{index}",
            "platform": "linkedin",
            "blocker_class": "linkedin_public_access_rate_limited",
        }
        for index in range(7)
    ]

    first = retryable_source_ids(
        {"sources": rows},
        "linkedin",
        shard_index=0,
        shard_count=1,
        limit=5,
        rotation_index=0,
    )
    second = retryable_source_ids(
        {"sources": rows},
        "linkedin",
        shard_index=0,
        shard_count=1,
        limit=5,
        rotation_index=1,
    )

    assert first == ["linkedin-0", "linkedin-1", "linkedin-2", "linkedin-3", "linkedin-4"]
    assert second == ["linkedin-5", "linkedin-6", "linkedin-0", "linkedin-1", "linkedin-2"]
    assert set(first + second) == {f"linkedin-{index}" for index in range(7)}
