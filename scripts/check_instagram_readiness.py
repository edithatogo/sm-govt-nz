"""Check Instagram Meta API readiness for controlled launch.

Outputs a structured JSON readiness report with:
- Secret presence (INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_USER_ID)
- Config state (instagram.enabled and related settings)
- Adapter test status
- Account type requirements documentation
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


INSTAGRAM_SECRET_NAMES = ["INSTAGRAM_ACCESS_TOKEN", "INSTAGRAM_USER_ID"]
ADAPTER_TEST_PATHS = ["tests/test_instagram_api_probe.py", "tests/test_syndication.py"]
CONFIG_PATH = Path("config.json")


def check_secrets(env: dict[str, str] | None = None) -> dict[str, Any]:
    """Check that Instagram secrets are configured in the environment."""
    active_env = env if env is not None else dict(os.environ)
    present: dict[str, bool] = {}
    for name in INSTAGRAM_SECRET_NAMES:
        present[name] = bool(active_env.get(name))

    all_present = all(present.values())
    return {
        "status": "passed" if all_present else "failed",
        "all_required_present": all_present,
        "secrets": present,
        "missing": [name for name, exists in present.items() if not exists],
    }


def check_config(env: dict[str, str] | None = None) -> dict[str, Any]:
    """Check that config.json has instagram settings configured."""
    _ = env  # reserved for future env-based config overrides
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
    instagram_setting = targets.get("instagram", {})
    if not instagram_setting:
        return {
            "status": "failed",
            "config_file_exists": True,
            "instagram_section_exists": False,
            "error": "No 'instagram' section in syndication_targets",
        }

    enabled = bool(instagram_setting.get("enabled", False))
    archive_replay = bool(instagram_setting.get("archive_replay_enabled", False))
    pipeline_stage = bool(instagram_setting.get("pipeline_stage_enabled", False))
    account_handle = str(instagram_setting.get("account_handle", "") or "")
    profile_url = str(instagram_setting.get("profile_url", "") or "")
    gated_by = str(instagram_setting.get("gated_by", "") or "")

    # Check if instagram is in any monitored account's syndicate_to list
    syndicate_to_configured = False
    for account in config.get("monitored_accounts", []):
        syndicate_to = account.get("syndicate_to", [])
        if "instagram" in syndicate_to:
            syndicate_to_configured = True
            break

    issues: list[str] = []
    if not enabled:
        issues.append("instagram.enabled is false")
    if gated_by and gated_by != "complete":
        issues.append(f"gated by: {gated_by}")

    return {
        "status": "passed",
        "config_file_exists": True,
        "instagram_section_exists": True,
        "enabled": enabled,
        "archive_replay_enabled": archive_replay,
        "pipeline_stage_enabled": pipeline_stage,
        "account_handle": account_handle,
        "profile_url": profile_url,
        "gated_by": gated_by,
        "syndicate_to_configured": syndicate_to_configured,
        "issues": issues,
        "launch_blocked": not enabled or bool(issues),
    }


def check_adapter_tests() -> dict[str, Any]:
    """Check that Instagram adapter tests exist and pass."""
    existing_tests = [p for p in ADAPTER_TEST_PATHS if Path(p).exists()]
    if not existing_tests:
        return {
            "status": "failed",
            "test_files_exist": False,
            "existing_test_files": [],
            "error": "No Instagram adapter test files found",
        }

    try:
        test_args = ["uv", "run", "pytest"] + existing_tests + ["-v", "--tb=short"]
        completed = subprocess.run(
            test_args, capture_output=True, text=True, timeout=120,
        )
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
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        return {
            "status": "failed",
            "test_files_exist": True,
            "existing_test_files": existing_tests,
            "all_tests_passed": False,
            "error": f"Could not run tests: {exc}",
        }


def account_type_requirements() -> dict[str, Any]:
    """Document Instagram account type requirements for publishing."""
    return {
        "required_account_type": "Professional (Business or Creator)",
        "personal_accounts": "NOT supported for API publishing",
        "why_professional": (
            "Meta's Instagram Graph API requires a Professional account "
            "(Business or Creator) to publish content via the API. Personal "
            "accounts cannot obtain the necessary publish permissions."
        ),
        "conversion_path": (
            "If the account is currently Personal, convert to Creator or "
            "Business via Instagram app Settings -> Account -> Switch to "
            "Professional account."
        ),
        "meta_app_permissions": [
            "instagram_basic",
            "instagram_content_publish",
            "pages_show_list",
            "business_management",
        ],
        "facebook_page_requirement": (
            "A Facebook Page linked to the same Meta Business account is "
            "required. The Instagram Professional account must be connected "
            "to a Facebook Page that is managed by the same Meta app."
        ),
        "token_lifetime_note": (
            "Instagram long-lived page access tokens typically last 60 days. "
            "Tokens expire on password change, de-auth, or when the app is "
            "removed. A token refresh should be scheduled before expiry."
        ),
        "app_review_note": (
            "Instagram content publishing requires app review approval for "
            "instagram_content_publish permission unless the app is in "
            "Development mode with only test users."
        ),
    }
