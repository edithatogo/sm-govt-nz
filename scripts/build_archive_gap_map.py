import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_archive_failure_triage_report import PRIORITY_DESCRIPTIONS, PRIORITY_BY_STATUS


SUCCESS_STATUSES = {
    "already_captured",
    "captured",
    "feed_already_captured",
    "feed_captured",
    "manual_seed_captured",
    "public_snapshot_already_captured",
    "public_snapshot_captured",
}

REPORT_ONLY_STATUSES = {"no_records", "feed_not_found", "browser_no_visible_posts"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def status_priority(status: str) -> str:
    if status in SUCCESS_STATUSES:
        return "archived_or_already_archived"
    if status in REPORT_ONLY_STATUSES:
        return "monitor_report_only"
    return PRIORITY_BY_STATUS.get(status, "review")


def build_gap_map(report_paths: list[Path]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    priority_counts: Counter[str] = Counter()
    platform_counts: Counter[str] = Counter()
    report_summaries: dict[str, Any] = {}
    for path in report_paths:
        report = load_json(path)
        results = report.get("results", [])
        if not isinstance(results, list):
            results = []
        report_summaries[str(path)] = report.get("summary", {})
        for row in results:
            if not isinstance(row, dict):
                continue
            status = str(row.get("status") or "unknown")
            priority = status_priority(status)
            platform = str(row.get("platform") or "unknown")
            status_counts[status] += 1
            priority_counts[priority] += 1
            platform_counts[platform] += 1
            if priority in {"archived_or_already_archived", "monitor_report_only"}:
                continue
            items.append(
                {
                    "source_id": str(row.get("source_id") or ""),
                    "agency_id": str(row.get("agency_id") or ""),
                    "platform": platform,
                    "url": str(row.get("url") or ""),
                    "status": status,
                    "reason": str(row.get("reason") or ""),
                    "priority": priority,
                    "priority_description": PRIORITY_DESCRIPTIONS.get(priority, "Needs review."),
                }
            )
    return {
        "inputs": {"reports": [str(path) for path in report_paths]},
        "summary": {
            "gap_count": len(items),
            "platform_counts": dict(sorted(platform_counts.items())),
            "priority_counts": dict(sorted(priority_counts.items())),
            "status_counts": dict(sorted(status_counts.items())),
        },
        "report_summaries": report_summaries,
        "gaps": items,
    }


def default_reports() -> list[Path]:
    conductor = Path("conductor")
    patterns = [
        "rss_archive_report.json",
        "json_feed_archive_report.json",
        "api_archive_report.json",
        "bluesky_archive_report.json",
        "youtube_archive*_report.json",
        "website_page_archive*_report.json",
        "threads_archive_report.json",
        "x_feed_archive_report.json",
        "linkedin_archive*_report.json",
        "newsletter_archive*_report.json",
    ]
    paths: list[Path] = []
    for pattern in patterns:
        paths.extend(sorted(conductor.glob(pattern)))
    return list(dict.fromkeys(paths))


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a prioritized archive gap map from archive reports.")
    parser.add_argument("--report", type=Path, action="append")
    parser.add_argument("--output", type=Path, default=Path("conductor/archive_gap_map.json"))
    args = parser.parse_args()
    report_paths = args.report or default_reports()
    gap_map = build_gap_map(report_paths)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(gap_map, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {args.output} with {gap_map['summary']['gap_count']} actionable gaps.")


if __name__ == "__main__":
    main()
