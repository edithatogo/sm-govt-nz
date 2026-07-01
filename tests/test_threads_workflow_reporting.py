from pathlib import Path


import argparse
import json
from pathlib import Path

from scripts.build_threads_seed_readiness_report import build_report, write_summary


def test_threads_workflows_write_dedicated_archive_report() -> None:
    manual = Path(".github/workflows/archive_threads_manual_seeds.yml").read_text(encoding="utf-8")
    scheduled = Path(".github/workflows/archive_threads_scheduled.yml").read_text(encoding="utf-8")

    assert "--report conductor/threads_archive_report.json" in manual
    assert "--report conductor/threads_archive_report.json" in scheduled
    assert "--path conductor/threads_archive_report.json" in manual
    assert "--path conductor/threads_archive_report.json" in scheduled
    assert "--path conductor/threads_seed_readiness_summary.md" in manual
    assert "THREADS_API_CAPTURE_ENABLED" in scheduled


def test_seed_missing_is_report_only_for_threads_readiness() -> None:
    workflow = Path(".github/workflows/validate_threads_manual_seeds.yml").read_text(encoding="utf-8")

    assert 'python-version: "3.14"' in workflow
    assert 'if item.get("readiness") in {"seed_empty", "seed_invalid"}' in workflow
    assert 'if item.get("readiness") in {"seed_missing", "seed_empty", "seed_invalid"}' not in workflow
    assert "Missing seed files are tracked in conductor reports only" in workflow
    assert "coverage gap tracked automatically" in workflow
    assert "gh issue close" in workflow


def test_invalid_or_empty_threads_seeds_remain_issue_worthy() -> None:
    workflow = Path(".github/workflows/validate_threads_manual_seeds.yml").read_text(encoding="utf-8")

    assert "seed_invalid" in workflow
    assert "seed_empty" in workflow
    assert "archive-input-needed" in workflow
    assert "gh issue create" in workflow


def test_threads_scheduled_workflow_closes_api_blocker_when_not_actionable() -> None:
    workflow = Path(".github/workflows/archive_threads_scheduled.yml").read_text(encoding="utf-8")

    assert 'THREADS_API_CAPTURE_ENABLED: ${{ vars.THREADS_API_CAPTURE_ENABLED || \'false\' }}' in workflow
    assert 'if result.get("status") in {"threads_permission_error", "threads_api_error"}' in workflow
    assert "if: ${{ inputs.dry_run != 'true' }}\n        env:\n          GH_TOKEN" not in workflow
    assert "gh issue close" in workflow
    assert "Live public Threads API capture is disabled" in workflow
    assert "Manual seeds remain the active automated capture path" in workflow


def test_threads_seed_readiness_report_writes_summary(tmp_path) -> None:
    manifest = tmp_path / "manifest.json"
    validation = tmp_path / "validation.json"
    summary_path = tmp_path / "summary.md"
    manifest.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "source_id": "threads-one",
                        "agency_id": "agency",
                        "agency_name": "Agency",
                        "platform": "threads",
                        "source_type": "threads",
                        "url": "https://www.threads.net/@agency",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    validation.write_text(json.dumps({"results": []}), encoding="utf-8")

    report = build_report(
        argparse.Namespace(
            manifest=manifest,
            seed_root=tmp_path / "manual_archive_seeds" / "threads",
            validation_report=validation,
        )
    )

    write_summary(summary_path, report)
    summary = summary_path.read_text(encoding="utf-8")
    assert "Threads Seed Readiness" in summary
    assert "`registered_threads_sources`: 1" in summary
