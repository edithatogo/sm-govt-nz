import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.archive_mirror_backlog import main


def cli() -> None:
    parser = argparse.ArgumentParser(description="Post bounded archive replay batches.")
    parser.add_argument("--target", default="bluesky")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--drain", action="store_true", help="Loop until all records are posted")
    args = parser.parse_args()

    summary = main(target=args.target, dry_run=args.dry_run, limit=args.limit, drain=args.drain)
    mode = "drain" if args.drain else f"batch (limit={args.limit})"
    print(
        f"{mode}: selected "
        f"{summary.selected} archive replay records for {args.target}; "
        f"posted {summary.posted} deliveries."
    )


if __name__ == "__main__":
    cli()
