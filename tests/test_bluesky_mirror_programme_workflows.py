from pathlib import Path


def test_posting_workflows_use_account_environments_and_kill_switch() -> None:
    for name in ("bluesky_mirror_ongoing.yml", "bluesky_mirror_historical_backfill.yml"):
        text = (Path(".github/workflows") / name).read_text(encoding="utf-8")
        assert "environment: ${{ matrix.environment }}" in text
        assert "vars.BLUESKY_MIRRORING_ENABLED == 'true'" in text
        assert "BLUESKY_APP_PASSWORD: ${{ secrets.BLUESKY_APP_PASSWORD }}" in text


def test_backfill_is_four_per_day_and_serial() -> None:
    text = Path(".github/workflows/bluesky_mirror_historical_backfill.yml").read_text(encoding="utf-8")
    assert 'cron: "17 */6 * * *"' in text
    assert "max-parallel: 1" in text


def test_legacy_follow_workflow_is_read_only() -> None:
    text = Path(".github/workflows/follow_sync.yml").read_text(encoding="utf-8")
    assert "contents: read" in text
    assert "--execute" not in text


def test_retired_syndicate_workflow_is_absent() -> None:
    assert not Path(".github/workflows/syndicate.yml").exists()


def test_posting_workflows_commit_only_account_partitioned_state() -> None:
    for name in (
        "bluesky_mirror_ongoing.yml",
        "bluesky_mirror_historical_backfill.yml",
    ):
        text = (Path(".github/workflows") / name).read_text(encoding="utf-8")
        assert "conductor/bluesky_mirror_state/${{ matrix.mirror_id }}.json" in text
        assert "conductor/bluesky_mirror_audit/${{ matrix.mirror_id }}.jsonl" in text
        assert "conductor/bluesky_mirror_runtime_state.json" not in text


def test_recovery_workflow_is_read_only_by_default_and_mirror_scoped() -> None:
    text = Path(".github/workflows/bluesky_mirror_recovery.yml").read_text(
        encoding="utf-8"
    )
    assert "default: false" in text
    assert "bluesky-mirror-recovery-${{ inputs.mirror_id }}" in text
    assert "conductor/bluesky_mirror_state/${{ inputs.mirror_id }}.json" in text
    assert "BLUESKY_APP_PASSWORD" not in text
    assert " publish " not in text


def test_credential_workflows_declare_app_password_mode_and_nonsecret_report() -> None:
    preflight = Path(".github/workflows/bluesky_mirror_preflight.yml").read_text(
        encoding="utf-8"
    )
    health = Path(".github/workflows/bluesky_mirror_health.yml").read_text(
        encoding="utf-8"
    )
    assert "BLUESKY_CREDENTIAL_MODE: app_password" in preflight
    assert "BLUESKY_CREDENTIAL_MODE: app_password" in health
    assert "credential-health --mirror-id" in health
    assert "bluesky_mirror_credential_health/${{ matrix.mirror_id }}.json" in health
