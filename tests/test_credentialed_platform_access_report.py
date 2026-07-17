import argparse
import json
from pathlib import Path

from scripts.build_credentialed_platform_access_report import build_report, write_summary


def write_inputs(tmp_path: Path):
    manifest = tmp_path / "manifest.json"
    policy = tmp_path / "policy.json"
    manifest.write_text(
        json.dumps(
            {
                "sources": [
                    {"source_id": "threads-one", "agency_id": "a", "platform": "threads", "account": "agency"},
                    {"source_id": "x-one", "agency_id": "a", "platform": "x", "account": "agency"},
                    {"source_id": "linkedin-one", "agency_id": "a", "platform": "linkedin", "account": "agency"},
                    {"source_id": "youtube-one", "agency_id": "a", "platform": "youtube", "account": "agency"},
                ]
            }
        ),
        encoding="utf-8",
    )
    policy.write_text(
        json.dumps(
            {
                "platforms": {
                    "threads": {
                        "gate_variable": "THREADS_API_CAPTURE_ENABLED",
                        "enabled_value": "true",
                        "required_secret_sets": [["THREADS_ACCESS_TOKEN"]],
                        "seed_directory": str(tmp_path / "manual_archive_seeds" / "threads"),
                        "default_capture_path": "operator_authorized_seed",
                        "disabled_status": "api_disabled_manual_seed_path",
                        "enabled_missing_secret_status": "api_enabled_missing_secret",
                        "enabled_ready_status": "api_enabled_ready",
                    },
                    "x": {
                        "gate_variable": "X_API_CAPTURE_ENABLED",
                        "enabled_value": "true",
                        "required_secret_sets": [["X_BEARER_TOKEN"], ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"]],
                        "seed_directory": str(tmp_path / "manual_archive_seeds" / "x"),
                        "default_capture_path": "public_snapshot_or_feed_then_operator_authorized_seed",
                        "disabled_status": "api_disabled_public_or_seed_path",
                        "enabled_missing_secret_status": "api_enabled_missing_secret",
                        "enabled_ready_status": "api_enabled_ready",
                    },
                    "linkedin": {
                        "gate_variable": "LINKEDIN_API_CAPTURE_ENABLED",
                        "enabled_value": "true",
                        "required_secret_sets": [["LINKEDIN_ACCESS_TOKEN"]],
                        "seed_directory": str(tmp_path / "manual_archive_seeds" / "linkedin"),
                        "default_capture_path": "operator_authorized_seed",
                        "disabled_status": "api_disabled_manual_seed_path",
                        "enabled_missing_secret_status": "api_enabled_missing_secret",
                        "enabled_ready_status": "api_enabled_ready",
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    return manifest, policy


def report_args(tmp_path: Path, manifest: Path, policy: Path):
    return argparse.Namespace(
        manifest=manifest,
        policy=policy,
        report=tmp_path / "report.json",
        summary=tmp_path / "summary.md",
        manual_seed_root=tmp_path / "manual_archive_seeds",
        platforms="threads,x,linkedin",
    )


def test_disabled_credentialed_gates_are_report_only(tmp_path, monkeypatch):
    monkeypatch.delenv("THREADS_API_CAPTURE_ENABLED", raising=False)
    monkeypatch.delenv("X_API_CAPTURE_ENABLED", raising=False)
    monkeypatch.delenv("LINKEDIN_API_CAPTURE_ENABLED", raising=False)
    manifest, policy = write_inputs(tmp_path)

    report = build_report(report_args(tmp_path, manifest, policy))

    assert report["summary"]["selected_sources"] == 3
    assert report["summary"]["status_counts"] == {
        "api_disabled_manual_seed_path": 2,
        "api_disabled_public_or_seed_path": 1,
    }
    assert report["summary"]["actionable_configuration_fault_count"] == 0
    assert report["actionable_configuration_faults"] == []


def test_enabled_gate_without_secret_is_actionable(tmp_path, monkeypatch):
    monkeypatch.setenv("THREADS_API_CAPTURE_ENABLED", "true")
    monkeypatch.delenv("THREADS_ACCESS_TOKEN", raising=False)
    manifest, policy = write_inputs(tmp_path)

    report = build_report(report_args(tmp_path, manifest, policy))

    assert report["summary"]["status_by_platform"]["threads"] == {"api_enabled_missing_secret": 1}
    assert report["summary"]["actionable_configuration_fault_count"] == 1
    assert report["actionable_configuration_faults"][0]["source_id"] == "threads-one"


def test_enabled_gate_with_one_secret_set_is_ready(tmp_path, monkeypatch):
    monkeypatch.setenv("X_API_CAPTURE_ENABLED", "true")
    monkeypatch.setenv("X_BEARER_TOKEN", "token")
    manifest, policy = write_inputs(tmp_path)

    report = build_report(report_args(tmp_path, manifest, policy))

    x_item = next(item for item in report["items"] if item["platform"] == "x")
    assert x_item["readiness_status"] == "api_enabled_ready"
    assert x_item["required_secrets_present"] is True
    assert x_item["present_secret_set_count"] == 1


def test_seed_presence_is_reported_but_does_not_make_api_ready(tmp_path, monkeypatch):
    monkeypatch.delenv("LINKEDIN_API_CAPTURE_ENABLED", raising=False)
    manifest, policy = write_inputs(tmp_path)
    seed_dir = tmp_path / "manual_archive_seeds" / "linkedin"
    seed_dir.mkdir(parents=True)
    (seed_dir / "linkedin-one.json").write_text('{"posts": []}', encoding="utf-8")

    report = build_report(report_args(tmp_path, manifest, policy))

    linkedin_item = next(item for item in report["items"] if item["platform"] == "linkedin")
    assert linkedin_item["seed_present"] is True
    assert linkedin_item["readiness_status"] == "api_disabled_manual_seed_path"
    assert report["summary"]["seed_present_by_platform"] == {"linkedin": 1}


def test_credentialed_report_writes_summary(tmp_path):
    manifest, policy = write_inputs(tmp_path)
    report = build_report(report_args(tmp_path, manifest, policy))
    summary_path = tmp_path / "summary.md"

    write_summary(summary_path, report)

    summary = summary_path.read_text(encoding="utf-8")
    assert "Credentialed Platform Access Readiness" in summary
    assert "Disabled live API gates are report-only" in summary


def test_normal_password_variables_are_reported_as_hygiene_faults(tmp_path, monkeypatch):
    monkeypatch.setenv("FACEBOOK_PASSWORD", "must-not-be-used")
    monkeypatch.delenv("LINKEDIN_PASSWORD", raising=False)
    manifest, policy = write_inputs(tmp_path)

    report = build_report(report_args(tmp_path, manifest, policy))

    assert report["credential_hygiene_faults"] == ["FACEBOOK_PASSWORD"]
    assert report["summary"]["credential_hygiene_fault_count"] == 1


def test_workflow_uses_gates_and_only_issues_for_enabled_missing_secrets():
    workflow = Path(".github/workflows/credentialed_platform_access_report.yml").read_text(encoding="utf-8")

    assert "THREADS_API_CAPTURE_ENABLED" in workflow
    assert "X_API_CAPTURE_ENABLED" in workflow
    assert "LINKEDIN_API_CAPTURE_ENABLED" in workflow
    assert "FACEBOOK_GRAPH_CAPTURE_ENABLED" in workflow
    assert "INSTAGRAM_GRAPH_CAPTURE_ENABLED" in workflow
    assert "api_enabled_missing_secret" not in workflow
    assert "actionable_configuration_faults" in workflow
    assert "Disabled credentialed gates and missing manual seeds are report-only states" in workflow
