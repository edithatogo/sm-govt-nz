import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_CHECKS = [
    ["ruff", "check", "--no-cache", "src", "tests", "scripts"],
    [sys.executable, "-m", "pytest", "-q"],
]


def run_checks(checks: list[list[str]] | None = None) -> dict[str, Any]:
    results = []
    for command in checks or DEFAULT_CHECKS:
        completed = subprocess.run(command, text=True, capture_output=True, check=False)
        results.append(
            {
                "command": command,
                "returncode": completed.returncode,
                "stdout": completed.stdout[-4000:],
                "stderr": completed.stderr[-4000:],
            }
        )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "success": all(result["returncode"] == 0 for result in results),
        "results": results,
        "suggested_actions": _suggest_actions(results),
    }


def write_report(report: dict[str, Any], path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2, ensure_ascii=False)
        file.write("\n")


def _suggest_actions(results: list[dict[str, Any]]) -> list[str]:
    actions = []
    for result in results:
        if result["returncode"] != 0:
            actions.append("Inspect failing command: " + " ".join(result["command"]))
    if not actions:
        actions.append("No immediate changes suggested; preserve current quality gate.")
    return actions


def main() -> None:
    parser = argparse.ArgumentParser(description="Run repository self-evaluation checks.")
    parser.add_argument("--output", default="agent_framework/evaluations/latest.json")
    args = parser.parse_args()
    write_report(run_checks(), args.output)


if __name__ == "__main__":
    main()