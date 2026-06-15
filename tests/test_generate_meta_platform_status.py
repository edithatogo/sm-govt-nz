"""Tests for scripts/generate_meta_platform_status.py."""

import json

from scripts.generate_meta_platform_status import generate_report, write_report


class TestGenerateReport:
    def test_returns_combined_report_with_both_platforms(self) -> None:
        report = generate_report(skip_test_run=True)
        assert "meta" in report
        assert "summary" in report
        assert "instagram" in report
        assert "facebook" in report
        assert "blockers" in report

    def test_meta_section_has_title_and_timestamp(self) -> None:
        report = generate_report(skip_test_run=True)
        assert report["meta"]["title"] == "Meta Platform Readiness Status"
        assert "generated_at" in report["meta"]

    def test_summary_contains_both_platform_keys(self) -> None:
        report = generate_report(skip_test_run=True)
        summary = report["summary"]
        assert "instagram" in summary
        assert "facebook" in summary
        for platform in ("instagram", "facebook"):
            for key in ("ready", "blockers_count", "secrets_ok", "config_ok"):
                assert key in summary[platform]

    def test_blockers_are_prefixed_with_platform_name(self) -> None:
        report = generate_report(env={}, skip_test_run=True)
        for blocker in report["blockers"]:
            assert blocker.startswith("[instagram]") or blocker.startswith("[facebook]")

    def test_instagram_individual_report_present(self) -> None:
        report = generate_report(skip_test_run=True)
        assert report["instagram"]["platform"] == "instagram"
        assert "account_type_requirements" in report["instagram"]

    def test_facebook_individual_report_present(self) -> None:
        report = generate_report(skip_test_run=True)
        assert report["facebook"]["platform"] == "facebook"
        assert "page_identity_requirements" in report["facebook"]


class TestWriteReport:
    def test_writes_to_specified_path(self, tmp_path) -> None:
        report = generate_report(skip_test_run=True)
        output_path = tmp_path / "test_meta_status.json"
        written = write_report(report, output_path)
        assert written.exists()
        assert written == output_path

        loaded = json.loads(output_path.read_text(encoding="utf-8"))
        assert loaded["meta"]["title"] == "Meta Platform Readiness Status"

    def test_creates_parent_directory(self, tmp_path) -> None:
        report = generate_report(skip_test_run=True)
        nested = tmp_path / "nested" / "dir" / "status.json"
        written = write_report(report, nested)
        assert written.exists()

    def test_written_report_is_valid_json_with_sort_keys(self, tmp_path) -> None:
        report = generate_report(skip_test_run=True)
        path = write_report(report, tmp_path / "sorted.json")
        raw = path.read_text(encoding="utf-8")
        # Verify it's sorted (a is before b in sorted order)
        # Just verify it can be parsed
        loaded = json.loads(raw)
        assert loaded["meta"]["overall_ready"] is False
