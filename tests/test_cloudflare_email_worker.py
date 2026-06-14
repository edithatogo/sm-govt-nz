import shutil
import subprocess
from pathlib import Path

import pytest


def test_cloudflare_email_worker_node_tests_pass() -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is not available")

    result = subprocess.run(
        [node, "--test", "cloudflare/courts_nz_email_worker.test.mjs"],
        cwd=Path(__file__).resolve().parents[1],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_cloudflare_email_worker_config_references_github_dispatch() -> None:
    worker = Path("cloudflare/courts_nz_email_worker.mjs").read_text(encoding="utf-8")
    config = Path("cloudflare/wrangler.courts-nz-email.toml.example").read_text(
        encoding="utf-8"
    )

    assert "courts_nz_email_received" in worker
    assert "https://api.github.com/repos/" in worker
    assert "GITHUB_TOKEN" in worker
    assert "ALLOWED_RECIPIENTS" in config
