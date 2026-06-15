"""Check Facebook Page Meta API readiness for controlled launch."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FACEBOOK_SECRET_NAMES = ["FACEBOOK_PAGE_ACCESS_TOKEN", "FACEBOOK_PAGE_ID"]
ADAPTER_TEST_PATHS = [
    "tests/test_facebook_page_probe.py",
    "tests/test_facebook_dry_run_latest.py",
    "tests/test_syndication.py",
]
CONFIG_PATH = Path("config.json")


def check_secrets(env: dict[str, str] | None = None) -> dict[str, Any]:
    active_env = env if env is not None else dict(os.environ)
    present = {name: bool(active_env.get(name)) for name in FACEBOOK_SECRET_NAMES}
    return {
        "status": "passed" if all(present.values()) else "failed",
        "all_required_present": all(present.values()),
        "secrets": present,
        "missing": [name for name, exists in present.items() if not exists],
    }


def check_config(env: dict[str, str] | None = None) -> dict[str, Any]:
    _ = env
    if not CONFIG_PATH.exists():
        return {
            "status": "failed",
            "config_file_exists": False,
            "error": f"config.json not found at {CONFIG_PATH}",
        }

    try:
        config: dict[str, Any] = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {
            "status": "failed",
            "config_file_exists": True,
            "error": f"config.json is not valid JSON: {exc}",
        }

    targets = config.get("syndication_targets", {})
    facebook = targets.get("facebook", {})
    if not facebook:
        return {
            "status": "failed",
            "config_file_exists": True,
            "facebook_section_exists": False,
            "error": "No facebook section in syndication_targets",
            "launch_blocked": True,
        }

    enabled = bool(facebook.get("enabled", False))
    gated_by = str(facebook.get("gated_by", "") or "")
    syndicate_to_configured = any(
        "facebook" in account.get("syndicate_to", [])
        for account in config.get("monitored_accounts", [])
    )
    issues: list[str] = []
    if not enabled:
        issues.append("facebook.enabled is false")
    if gated_by and gated_by != "complete":
        issues.append(f"gated by: {gated_by}")

    return {
        "status": "passed",
        "config_file_exists": True,
        "facebook_section_exists": True,
        "enabled": enabled,
        "archive_replay_enabled": bool(facebook.get("archive_replay_enabled", False)),
        "pipeline_stage_enabled": bool(facebook.get("pipeline_stage_enabled", False)),
        "account_handle": str(facebook.get("account_handle", "") or ""),
        "profile_url": str(facebook.get("profile_url", "") or ""),
        "gated_by": gated_by,
        "syndicate_to_configured": syndicate_to_configured,
        "issues": issues,
        "launch_blocked": not enabled or bool(issues),
    }


def check_adapter_tests() -> dict[str, Any]:
    existing_tests = [path for path in ADAPTER_TEST_PATHS if Path(path).exists()]
    if not existing_tests:
        return {
            "status": "failed",
            "test_files_exist": False,
            "existing_test_files": [],
            "error": "No Facebook adapter test files found",
        }

    try:
        completed = subprocess.run(
            ["uv", "run", "pytest", *existing_tests, "-v", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        return {
            "status": "failed",
            "test_files_exist": True,
            "existing_test_files": existing_tests,
            "all_tests_passed": False,
            "error": f"Could not run tests: {exc}",
        }

    passed = completed.returncode == 0
    return {
        "status": "passed" if passed else "failed",
        "test_files_exist": True,
        "existing_test_files": existing_tests,
        "all_tests_passed": passed,
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def page_identity_requirements() -> dict[str, Any]:
    return {
        "required_identity": "Dedicated Facebook Page, not personal profile",
        "personal_profiles": "Not supported for API publishing",
        "meta_app_permissions": [
            "pages_manage_posts",
            "pages_read_engagement",
            "pages_show_list",
            "business_management",
        ],
        "page_access_token_requirement": (
            "A Page Access Token with pages_manage_posts permission is required."
        ),
        "app_review_note": (
            "pages_manage_posts requires app review for production use. In development mode, "
            "only test users with Page roles can publish."
        ),
    }


def check_readiness(
    env: dict[str, str] | None = None,
    *,
    skip_test_run: bool = False,
) -> dict[str, Any]:
    secrets_result = check_secrets(env)
    config_result = check_config(env)
    tests_result = (
        {"status": "skipped", "note": "Test execution skipped (--skip-test-run flag)"}
        if skip_test_run
        else check_adapter_tests()
    )

    ready = (
        secrets_result["status"] == "passed"
        and config_result["status"] == "passed"
        and (tests_result["status"] == "skipped" or tests_result["status"] == "passed")
    )
    blockers: list[str] = []
    if secrets_result["status"] != "passed":
        blockers.append(f"Missing secrets: {', '.join(secrets_result['missing'])}")
    if config_result.get("launch_blocked", True):
        blockers.append("Facebook is not enabled or remains gated in config.json")
    if tests_result.get("status") == "failed":
        blockers.append("Facebook adapter tests are failing")

    return {
        "platform": "facebook",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ready": ready,
        "blockers": blockers,
        "secrets": secrets_result,
        "config": config_result,
        "adapter_tests": tests_result,
        "page_identity_requirements": page_identity_requirements(),
    }


def _print_human_readable(report: dict[str, Any]) -> None:
    print(f"=== Facebook Readiness Report ({report['timestamp']}) ===")
    print(f"Ready: {report['ready']}")
    if report["blockers"]:
        print("Blockers:")
        for blocker in report["blockers"]:
            print(f"  - {blocker}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check Facebook Page Meta API readiness for controlled launch."
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--skip-test-run", action="store_true", help="Skip running adapter tests")
    args = parser.parse_args()

    report = check_readiness(skip_test_run=args.skip_test_run)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        _print_human_readable(report)
    sys.exit(0 if report["ready"] else 1)


if __name__ == "__main__":
    main()
