import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.rss_discovery import discover_courts_rss_feeds, write_rss_discovery_report
from src.source_inventory import load_source_inventory


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover Courts of New Zealand RSS/Atom feeds.")
    parser.add_argument("--inventory", default="config/courts_nz_sources.json")
    parser.add_argument("--output", default="config/courts_nz_rss_feeds.json")
    args = parser.parse_args()

    report = discover_courts_rss_feeds(load_source_inventory(args.inventory))
    write_rss_discovery_report(report, args.output)
    print(json.dumps(asdict(report), indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
