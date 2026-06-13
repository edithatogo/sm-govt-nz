import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.archive_mirror_backlog import main


def cli() -> None:
    parser = argparse.ArgumentParser(description="Post bounded archive replay batches.")
    parser.add_argument("--target", default="bluesky")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    summary = main(target=args.target, dry_run=args.dry_run)
    print(
        "Selected "
        f"{summary.selected} archive replay records for {args.target}; "
        f"posted {summary.posted} deliveries."
    )


if __name__ == "__main__":
    cli()
