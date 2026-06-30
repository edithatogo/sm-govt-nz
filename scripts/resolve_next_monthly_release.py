import argparse
import os
import sys
from pathlib import Path

try:
    from scripts.build_monthly_release_plan import build_plan
except ModuleNotFoundError:
    ROOT = Path(__file__).resolve().parents[1]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.build_monthly_release_plan import build_plan


def _write_outputs(values: dict[str, str]) -> None:
    output_path = os.getenv("GITHUB_OUTPUT")
    lines = [f"{key}={value}" for key, value in values.items()]
    if output_path:
        with Path(output_path).open("a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
    else:
        print("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve the next deterministic retrospective monthly release.")
    parser.add_argument("--normalized-root", type=Path, default=Path("historical_archive_normalized"))
    parser.add_argument("--status-report", type=Path, default=Path("conductor/archive_publication_status.json"))
    parser.add_argument("--ledger", type=Path, default=Path("conductor/monthly_release_ledger.json"))
    args = parser.parse_args()
    plan = build_plan(args.normalized_root, args.status_report, args.ledger)
    candidates = [item for item in plan.get("months", []) if item.get("status") == "candidate"]
    if not candidates:
        _write_outputs({"should_publish": "false", "release_version": ""})
        return
    release_version = str(candidates[0]["release_version"])
    _write_outputs({"should_publish": "true", "release_version": release_version})


if __name__ == "__main__":
    main()
