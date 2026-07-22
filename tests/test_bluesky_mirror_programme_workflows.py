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
