import json
from pathlib import Path

from scripts.manage_bluesky_mirror_programme import (
    github_matrix_outputs,
    write_json_report,
)


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


def test_cleanup_verification_workflow_has_no_delete_or_write_credentials() -> None:
    text = Path(
        ".github/workflows/bluesky_mirror_cleanup_verification.yml"
    ).read_text(encoding="utf-8")
    assert "--reconcile-programme" in text
    assert "--report-only" in text
    assert "BLUESKY_APP_PASSWORD" not in text
    assert "delete" not in text.casefold()
    assert "conductor/bluesky_mirror_cleanup/${{ matrix.mirror_id }}.json" in text


def test_manual_matrix_workflows_are_mirror_scoped_and_summarized() -> None:
    modes = {
        "bluesky_mirror_preflight.yml": "preflight",
        "bluesky_mirror_ongoing.yml": "ongoing",
        "bluesky_mirror_historical_backfill.yml": "backfill",
        "bluesky_mirror_health.yml": "health",
    }
    for name, mode in modes.items():
        text = (Path(".github/workflows") / name).read_text(encoding="utf-8")
        assert "mirror_id:" in text
        assert "required: true" in text
        assert "MIRROR_ID: ${{ inputs.mirror_id }}" in text
        assert f'matrix --mode {mode} --mirror-id "$MIRROR_ID"' in text
        assert "GITHUB_STEP_SUMMARY" in text


def test_posting_workflow_jobs_use_account_specific_concurrency() -> None:
    for name in (
        "bluesky_mirror_ongoing.yml",
        "bluesky_mirror_historical_backfill.yml",
    ):
        text = (Path(".github/workflows") / name).read_text(encoding="utf-8")
        assert "group: bluesky-mirror-${{ matrix.mirror_id }}" in text


def test_recovery_workflow_discloses_selected_mirror() -> None:
    text = Path(".github/workflows/bluesky_mirror_recovery.yml").read_text(
        encoding="utf-8"
    )
    assert "GITHUB_STEP_SUMMARY" in text
    assert "SELECTED_MIRROR: ${{ inputs.mirror_id }}" in text
    assert "printf '%s\\n' \"$SELECTED_MIRROR\"" in text


def test_manual_inputs_are_not_interpolated_directly_into_shell_commands() -> None:
    names = (
        "bluesky_mirror_emergency_pause.yml",
        "bluesky_mirror_health.yml",
        "bluesky_mirror_historical_backfill.yml",
        "bluesky_mirror_ongoing.yml",
        "bluesky_mirror_preflight.yml",
        "bluesky_mirror_recovery.yml",
    )
    for name in names:
        text = (Path(".github/workflows") / name).read_text(encoding="utf-8")
        forbidden = (
            "--mirror-id '${{ inputs.",
            "--reason '${{ inputs.",
            'if [ "${{ inputs.',
        )
        for fragment in forbidden:
            assert fragment not in text, f"{name}: {fragment}"


def test_json_report_writer_creates_missing_parent_directories(tmp_path: Path) -> None:
    output = tmp_path / "nested" / "credential-health.json"

    write_json_report(output, {"valid": True})

    assert json.loads(output.read_text(encoding="utf-8")) == {"valid": True}


def test_empty_matrix_outputs_are_safe_and_report_the_true_selection() -> None:
    outputs = github_matrix_outputs({"include": []})

    assert outputs["has_targets"] is False
    assert outputs["selected_matrix"] == {"include": []}
    assert outputs["matrix"] == {
        "include": [
            {
                "skip": True,
                "mirror_id": "__no_eligible_mirror__",
                "environment": "__no_environment__",
            }
        ]
    }


def test_nonempty_matrix_outputs_are_unchanged() -> None:
    matrix = {
        "include": [
            {
                "mirror_id": "agency",
                "environment": "bluesky-mirror-agency",
            }
        ]
    }
    outputs = github_matrix_outputs(matrix)

    assert outputs["has_targets"] is True
    assert outputs["selected_matrix"] == matrix
    assert outputs["matrix"] == matrix


def test_posting_workflows_treat_empty_matrices_as_successful_noops() -> None:
    for name in (
        "bluesky_mirror_ongoing.yml",
        "bluesky_mirror_historical_backfill.yml",
    ):
        text = (Path(".github/workflows") / name).read_text(encoding="utf-8")
        assert "selected_matrix: ${{ steps.matrix.outputs.selected_matrix }}" in text
        assert "has_targets: ${{ steps.matrix.outputs.has_targets }}" in text
        assert "no-eligible-mirrors:" in text
        assert "needs.plan.outputs.has_targets != 'true'" in text
        assert "needs.plan.outputs.has_targets == 'true'" in text
