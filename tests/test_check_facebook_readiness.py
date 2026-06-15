"""Tests for scripts/check_facebook_readiness.py."""

from scripts.check_facebook_readiness import (
    check_config,
    check_readiness,
    check_secrets,
    page_identity_requirements,
)


class TestCheckSecrets:
    def test_all_secrets_present(self) -> None:
        env = {"FACEBOOK_PAGE_ACCESS_TOKEN": "tok", "FACEBOOK_PAGE_ID": "123"}
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
        env = {"FACEBOOK_PAGE_ID": "123"}
        result = check_secrets(env)
        assert result["status"] == "failed"
        assert result["missing"] == ["FACEBOOK_PAGE_ACCESS_TOKEN"]


class TestCheckConfig:
    def test_config_exists_with_facebook_section(self) -> None:
        result = check_config()
        assert result["config_file_exists"] is True
        assert result["facebook_section_exists"] is True
        assert result["launch_blocked"] is True  # currently disabled

    def test_facebook_section_has_gated_by(self) -> None:
        result = check_config()
        assert result["gated_by"] != ""


class TestPageIdentityRequirements:
    def test_requires_dedicated_page(self) -> None:
        reqs = page_identity_requirements()
        assert "Dedicated Facebook Page" in reqs["required_identity"]
        assert "NOT supported" in reqs["personal_profiles"]

    def test_lists_required_permissions(self) -> None:
        reqs = page_identity_requirements()
        assert "pages_manage_posts" in reqs["meta_app_permissions"]
        assert len(reqs["meta_app_permissions"]) >= 3


class TestCheckReadiness:
    def test_returns_structured_report(self) -> None:
        report = check_readiness(skip_test_run=True)
        assert report["platform"] == "facebook"
        assert "timestamp" in report
        assert "ready" in report
        assert "secrets" in report
        assert "config" in report
        assert "adapter_tests" in report
        assert "page_identity_requirements" in report
        assert "blockers" in report

    def test_secrets_fail_when_not_set(self) -> None:
        report = check_readiness(env={}, skip_test_run=True)
        assert report["ready"] is False
        assert any("Missing secrets" in b for b in report["blockers"])

    def test_secrets_pass_when_set(self) -> None:
        env = {"FACEBOOK_PAGE_ACCESS_TOKEN": "tok", "FACEBOOK_PAGE_ID": "id"}
        report = check_readiness(env=env, skip_test_run=True)
        assert report["secrets"]["status"] == "passed"

    def test_blockers_include_config_disabled(self) -> None:
        env = {"FACEBOOK_PAGE_ACCESS_TOKEN": "tok", "FACEBOOK_PAGE_ID": "id"}
        report = check_readiness(env=env, skip_test_run=True)
        assert report["config"]["launch_blocked"] is True
        assert any("not enabled" in b for b in report["blockers"])

    def test_main_runs_without_crashing(self, capsys) -> None:
        import sys
        from scripts.check_facebook_readiness import main

        test_args = ["check_facebook_readiness.py", "--skip-test-run", "--json"]
        try:
            sys.argv = test_args
            main()
        except SystemExit as exc:
            assert exc.code == 1
        captured = capsys.readouterr()
        output = captured.out + captured.err
        assert "facebook" in output.lower() or "blockers" in output.lower()
