import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
GAP_MAP = ROOT / "conductor" / "archive_gap_map.json"


def run_command(args: list[str]) -> None:
    completed = subprocess.run(args, cwd=ROOT, check=False, text=True)
    if completed.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(args)}")


def load_gap_map() -> dict[str, Any]:
    return json.loads(GAP_MAP.read_text(encoding="utf-8"))


def p1_count(gap_map: dict[str, Any]) -> int:
    return int(gap_map.get("summary", {}).get("priority_counts", {}).get("p1_existing_resources", 0))


def main() -> None:
    parser = argparse.ArgumentParser(description="Repeat repo-resolvable archive remediation until the p1 backlog stabilizes.")
    parser.add_argument("--max-iterations", type=int, default=2)
    parser.add_argument("--source-types", default="website_page,youtube")
    args = parser.parse_args()

    source_types = [part.strip() for part in args.source_types.split(",") if part.strip()]
    if not source_types:
        raise SystemExit("No source types supplied.")

    previous_p1 = None
    for iteration in range(1, args.max_iterations + 1):
        print(f"Iteration {iteration}/{args.max_iterations}")
        for source_type in source_types:
            print(f"  Archiving {source_type}...")
            run_command(
                [
                    sys.executable,
                    "scripts/archive_registered_sources.py",
                    "--source-type",
                    source_type,
                    "--include-blocked",
                    "--retry-gap-map-from",
                    str(GAP_MAP),
                ]
            )
        print("  Rebuilding archive gap map...")
        run_command([sys.executable, "scripts/build_archive_gap_map.py"])
        gap_map = load_gap_map()
        current_p1 = p1_count(gap_map)
        print(f"  p1_existing_resources={current_p1}")
        if current_p1 == 0:
            print("  Stop condition reached: no repo-resolvable p1 backlog remains.")
            return
        if previous_p1 is not None and current_p1 >= previous_p1:
            print("  Stop condition reached: p1 backlog did not improve.")
            return
        previous_p1 = current_p1

    print("Reached max iterations without eliminating the p1 backlog.")


if __name__ == "__main__":
    main()
