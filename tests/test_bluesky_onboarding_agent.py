import json
import subprocess
import sys
from pathlib import Path


def test_direct_plan_execution_uses_pilot_ranking() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/bluesky_onboarding_agent.py",
            "plan",
            "--limit",
            "1",
        ],
        cwd=Path(__file__).resolve().parents[1],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["candidates"][0]["mirror_id"] == "electoral-commission"
