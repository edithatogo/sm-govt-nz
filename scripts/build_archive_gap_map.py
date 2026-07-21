import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_archive_failure_triage_report import PRIORITY_DESCRIPTIONS, PRIORITY_BY_STATUS  # noqa: E402


SUCCESS_STATUSES = {
    "already_captured",
    "browser_already_captured",
    "browser_captured",
    "captured",
    "feed_already_captured",
    "feed_captured",
    "manual_seed_captured",
    "public_snapshot_already_captured",
    "public_snapshot_captured",
    "seed_present",
}

REPORT_ONLY_STATUSES = {
    "browser_captcha_or_challenge",
    "browser_login_required",
    "browser_no_visible_content",
    "browser_no_visible_posts",
    "feed_not_found",
    "no_records",
    "youtube_video_metadata_blocked",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def report_path(path: Path) -> str:
    return path.as_posix()


def status_priority(status: str) -> str:
    if status in SUCCESS_STATUSES:
        return "archived_or_already_archived"
    if status in REPORT_ONLY_STATUSES:
        return "monitor_report_only"
    if status == "needs_authorized_seed_or_api":
        return "p2_existing_system_needs_seed_input"
    return PRIORITY_BY_STATUS.get(status, "review")


def source_key(row: dict[str, Any]) -> str:
    source_id = str(row.get("candidate_id") or row.get("source_id") or "")
    if source_id:
        return source_id
    return f"{row.get('platform') or ''}|{row.get('url') or ''}"


def merge_rows(existing: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    existing_priority = status_priority(str(existing.get("status") or ""))
    candidate_priority = status_priority(str(candidate.get("status") or ""))
    rank = {"archived_or_already_archived": 0, "monitor_report_only": 1}
    existing_rank = rank.get(existing_priority, 2)
    candidate_rank = rank.get(candidate_priority, 2)
    if candidate_rank < existing_rank or candidate_rank == existing_rank:
        merged = dict(candidate)
        merged["supersedes_status"] = existing.get("status", "")
        merged["supersedes_report"] = existing.get("report", "")
        return merged
    return existing


def report_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    results = report.get("results", [])
    if isinstance(results, list) and results:
        return [row for row in results if isinstance(row, dict)]
    items = report.get("items", [])
    if not isinstance(items, list):
        return []
    rows = []
    for item in items:
        if not isinstance(item, dict):
            continue
        row = dict(item)
        row["status"] = row.get("status") or row.get("onboarding_status") or "unknown"
        if row["status"] == "needs_authorized_seed_or_api" and not row.get("reason"):
            row["reason"] = "authorized seed, owner export, or approved API access is required"
        rows.append(row)
    return rows


def build_gap_map(report_paths: list[Path]) -> dict[str, Any]:
    rows_by_source: dict[str, dict[str, Any]] = {}
    input_status_counts: Counter[str] = Counter()
    report_summaries: dict[str, Any] = {}
    for path in report_paths:
        report = load_json(path)
        report_summaries[report_path(path)] = report.get("summary", {})
        for row in report_rows(report):
            source_id = source_key(row)
            if not source_id:
                continue
            row_with_report = dict(row)
            row_with_report["report"] = report_path(path)
            input_status_counts[str(row.get("status") or "unknown")] += 1
            if source_id in rows_by_source:
                rows_by_source[source_id] = merge_rows(rows_by_source[source_id], row_with_report)
            else:
                rows_by_source[source_id] = row_with_report

    items: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    priority_counts: Counter[str] = Counter()
    platform_counts: Counter[str] = Counter()
    superseded_count = sum(1 for row in rows_by_source.values() if row.get("supersedes_status"))
    for row in rows_by_source.values():
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
                "report": str(row.get("report") or ""),
                "supersedes_status": str(row.get("supersedes_status") or ""),
                "supersedes_report": str(row.get("supersedes_report") or ""),
            }
        )
    return {
        "inputs": {"reports": [report_path(path) for path in report_paths]},
        "summary": {
            "gap_count": len(items),
            "platform_counts": dict(sorted(platform_counts.items())),
            "priority_counts": dict(sorted(priority_counts.items())),
            "input_status_counts": dict(sorted(input_status_counts.items())),
            "status_counts": dict(sorted(status_counts.items())),
            "superseded_source_count": superseded_count,
        },
        "report_summaries": report_summaries,
        "gaps": items,
    }


def default_reports() -> list[Path]:
    conductor = Path("conductor")
    names = [
        "rss_archive_report.json",
        "json_feed_archive_report.json",
        "api_archive_report.json",
        "bluesky_archive_report.json",
        "youtube_archive_report.json",
        "website_archive_report.json",
        "website_browser_archive_report.json",
        "threads_archive_report.json",
        "x_feed_archive_report.json",
        "x_browser_and_feed_archive_report.json",
        "linkedin_archive_report.json",
        "newsletter_archive_report.json",
        "manual_seed_onboarding_report.json",
    ]
    paths: list[Path] = []
    for name in names:
        path = conductor / name
        if path.is_file():
            paths.append(path)
    paths.extend(sorted(conductor.glob("*_archive_paced_retry_report.json")))
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
