import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.bluesky_backlog import main


def cli() -> None:
    parser = argparse.ArgumentParser(description="Post bounded Bluesky historical backlog batches.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    summary = main(dry_run=args.dry_run)
    print(f"Selected {summary.selected} backlog records; posted {summary.posted} deliveries.")


if __name__ == "__main__":
    cli()
