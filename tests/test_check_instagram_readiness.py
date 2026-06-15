"""Tests for scripts/check_instagram_readiness.py."""

import json
from pathlib import Path

from scripts.check_instagram_readiness import (
    account_type_requirements,
    check_config,
    check_readiness,
    check_secrets,
)


class TestCheckSecrets:
    def test_all_secrets_present(self) -> None:
        env = {"INSTAGRAM_ACCESS_TOKEN": "token", "INSTAGRAM_USER_ID": "123"}
        result = check_secrets(env)
        assert result["status"] == "passed"
        assert result["all_required_present"] is True
        assert result["missing"] == []

    def test_missing_all_secrets(self) -> None:
        result = check_secrets({})
        assert result["status"] == "failed"
        assert result["all_required_present"] is False
        assert len(result["missing"]) == 2

    def test_missing_one_secret(self) -> None:
        env = {"INSTAGRAM_ACCESS_TOKEN": "token"}
        result = check_secrets(env)
        assert result["status"] == "failed"
        assert result["all_required_present"] is False
        assert result["missing"] == ["INSTAGRAM_USER_ID"]


class TestCheckConfig:
    def test_config_exists_with_instagram_section(self) -> None:
        result = check_config()
        assert result["config_file_exists"] is True
        assert result["instagram_section_exists"] is True
        assert result["account_handle"] != ""
        assert result["launch_blocked"] is True  # currently disabled

    def test_instagram_section_has_correct_profile_url(self) -> None:
        result = check_config()
        assert "instagram.com" in result["profile_url"]


class TestAccountTypeRequirements:
    def test_requires_professional_account(self) -> None:
        reqs = account_type_requirements()
        assert "Professional" in reqs["required_account_type"]
        assert "NOT supported" in reqs["personal_accounts"]

    def test_lists_required_permissions(self) -> None:
        reqs = account_type_requirements()
        assert "instagram_content_publish" in reqs["meta_app_permissions"]
        assert len(reqs["meta_app_permissions"]) >= 3


class TestCheckReadiness:
    def test_returns_structured_report(self) -> None:
        report = check_readiness(skip_test_run=True)
        assert report["platform"] == "instagram"
        assert "timestamp" in report
        assert "ready" in report
        assert "secrets" in report
        assert "config" in report
        assert "adapter_tests" in report
        assert "account_type_requirements" in report
        assert "blockers" in report

    def test_secrets_fail_when_not_set(self) -> None:
        report = check_readiness(env={}, skip_test_run=True)
        assert report["ready"] is False
        assert any("Missing secrets" in b for b in report["blockers"])

    def test_secrets_pass_when_set(self) -> None:
        env = {"INSTAGRAM_ACCESS_TOKEN": "tok", "INSTAGRAM_USER_ID": "id"}
        report = check_readiness(env=env, skip_test_run=True)
        assert report["secrets"]["status"] == "passed"

    def test_blockers_include_config_disabled(self) -> None:
        env = {"INSTAGRAM_ACCESS_TOKEN": "tok", "INSTAGRAM_USER_ID": "id"}
        report = check_readiness(env=env, skip_test_run=True)
        assert report["config"]["launch_blocked"] is True
        assert any("not enabled" in b for b in report["blockers"])

    def test_unexpected_args_do_not_crash_main(self, capsys) -> None:
        """Verify main() handles --help gracefully or validates args."""
        import sys
        from scripts.check_instagram_readiness import main

        test_args = ["check_instagram_readiness.py", "--skip-test-run", "--json"]
        try:
            sys.argv = test_args
            main()
        except SystemExit as exc:
            # Expect exit 1 because secrets missing, not a crash
            assert exc.code == 1
        captured = capsys.readouterr()
        output = captured.out + captured.err
        assert "Instagram" in output or "timestamp" in output
