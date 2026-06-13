import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.archive_mirror_coverage import write_archive_mirror_coverage_report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Report archive replay coverage for mirror platforms."
    )
    parser.add_argument("--output", default="conductor/archive_mirror_coverage.json")
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()

    report = write_archive_mirror_coverage_report(args.output)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    if args.require_complete and not report.complete:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
