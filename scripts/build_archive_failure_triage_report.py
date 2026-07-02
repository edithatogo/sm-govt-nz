import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SUCCESS_STATUSES = {"captured", "already_captured", "would_capture", "manual_seed_captured"}
REPORT_ONLY_STATUSES_BY_PLATFORM = {
    ("youtube", "no_records"): "monitor_zero_record_channel",
}

ACTION_BY_STATUS = {
    "capture_blocked": "review_access_or_mark_blocked",
    "capture_failed": "review_url_or_adapter",
    "dns_failed": "verify_url_or_mark_stale",
    "method_not_allowed": "retry_with_get_and_alternate_host",
    "network_error": "retry_later",
    "no_records": "monitor_or_verify_channel_activity",
    "not_acceptable": "retry_with_browser_headers_or_alternate_url",
    "not_found": "verify_url_or_mark_retired",
    "source_url_not_channel": "replace_with_channel_url_or_mark_video_seed",
    "tls_failed": "review_tls_or_alternate_url",
    "youtube_channel_not_found": "verify_handle_or_mark_retired",
    "youtube_channel_unresolved": "verify_channel_page_or_mark_unresolved",
    "youtube_video_metadata_blocked": "record_video_metadata_unavailable_or_supply_seed",
    "youtube_video_not_found": "verify_video_url_or_mark_retired",
    "manual_seed_missing": "supply_operator_authorized_seed",
    "seed_empty": "replace_empty_seed_with_authorized_records",
    "seed_invalid": "fix_seed_json_or_required_fields",
}

PRIORITY_BY_STATUS = {
    "capture_failed": "p1_existing_resources",
    "dns_failed": "p1_existing_resources",
    "method_not_allowed": "p1_existing_resources",
    "network_error": "p1_existing_resources",
    "network_timeout": "p1_existing_resources",
    "not_acceptable": "p1_existing_resources",
    "not_found": "p1_existing_resources",
    "tls_failed": "p1_existing_resources",
    "manual_seed_missing": "p2_existing_system_needs_seed_input",
    "seed_empty": "p2_existing_system_needs_seed_input",
    "seed_invalid": "p2_existing_system_needs_seed_input",
    "auth_required": "p3_needs_operator_or_platform_access",
    "youtube_video_metadata_blocked": "p3_needs_operator_or_platform_access",
    "youtube_video_not_found": "p1_existing_resources",
    "capture_blocked": "p4_larger_browser_or_access_project",
}

PRIORITY_DESCRIPTIONS = {
    "p1_existing_resources": "Can be improved with existing repo resources and keyless public retries.",
    "p2_existing_system_needs_seed_input": "Existing archive system is ready, but operator-authorized seed input is missing.",
    "p3_needs_operator_or_platform_access": "Needs login/export/API access before capture can lawfully proceed.",
    "p4_larger_browser_or_access_project": "Requires a larger browser/API/access project and careful policy boundaries.",
}

def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def fixability_class(platform: str, status: str) -> str:
    if platform == "website_page" and status in {"dns_failed", "method_not_allowed", "network_timeout", "network_error", "not_acceptable", "not_found", "tls_failed"}:
        return "retry_or_url_canonicalization"
    if platform == "website_page" and status == "capture_blocked":
        return "browser_fallback_candidate"
    if platform == "youtube" and status in {"capture_failed", "source_url_not_channel", "youtube_channel_not_found", "youtube_channel_unresolved", "youtube_video_not_found"}:
        return "youtube_url_or_channel_resolution"
    if platform == "youtube" and status == "youtube_video_metadata_blocked":
        return "youtube_video_metadata_unavailable"
    if status in {"manual_seed_missing", "seed_empty", "seed_invalid"}:
        return "operator_seed_input"
    return "review"


def triage_item(report_path: Path, row: dict[str, Any]) -> dict[str, Any]:
    status = str(row.get("status") or "unknown")
    source_id = str(row.get("source_id") or "")
    platform = str(row.get("platform") or "")
    agency_id = str(row.get("agency_id") or "")
    url = str(row.get("url") or "")
    reason = str(row.get("reason") or "")
    priority = PRIORITY_BY_STATUS.get(status, "review")
    return {
        "source_id": source_id,
        "agency_id": agency_id,
        "platform": platform,
        "url": url,
        "status": status,
        "reason": reason,
        "recommended_action": ACTION_BY_STATUS.get(status, "review"),
        "fixability_class": fixability_class(platform, status),
        "priority": priority,
        "priority_description": PRIORITY_DESCRIPTIONS.get(priority, "Needs review."),
        "report": str(report_path),
    }


def report_only_action(row: dict[str, Any]) -> str:
    platform = str(row.get("platform") or "")
    status = str(row.get("status") or "unknown")
    return REPORT_ONLY_STATUSES_BY_PLATFORM.get((platform, status), "")


def build_report(report_paths: list[Path]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    report_only_items: list[dict[str, Any]] = []
    report_summaries: dict[str, Any] = {}
    for report_path in report_paths:
        report = load_json(report_path)
        if not isinstance(report, dict):
            report = {"schema_error": f"expected object report, got {type(report).__name__}"}
        report_summaries[str(report_path)] = {
            "generated_at": report.get("generated_at"),
            "dry_run": report.get("dry_run"),
            "summary": report.get("summary", {}),
        }
        results = report.get("results", [])
        if not isinstance(results, list):
            results = []
        for row in results:
            if not isinstance(row, dict):
                continue
            if row.get("status") in SUCCESS_STATUSES:
                continue
            report_only = report_only_action(row)
            if report_only:
                item = triage_item(report_path, row)
                item["recommended_action"] = report_only
                item["report_only"] = True
                report_only_items.append(item)
                continue
            items.append(triage_item(report_path, row))
    status_counts = Counter(item["status"] for item in items)
    platform_counts = Counter(item["platform"] for item in items)
    priority_counts = Counter(item["priority"] for item in items)
    report_only_status_counts = Counter(item["status"] for item in report_only_items)
    report_only_platform_counts = Counter(item["platform"] for item in report_only_items)
    report_only_priority_counts = Counter(item["priority"] for item in report_only_items)
    return {
        "generated_at": now_iso(),
        "inputs": {"reports": [str(path) for path in report_paths]},
        "report_summaries": report_summaries,
        "summary": {
            "failure_count": len(items),
            "platform_counts": dict(sorted(platform_counts.items())),
            "report_only_count": len(report_only_items),
            "report_only_platform_counts": dict(sorted(report_only_platform_counts.items())),
            "report_only_priority_counts": dict(sorted(report_only_priority_counts.items())),
            "report_only_status_counts": dict(sorted(report_only_status_counts.items())),
            "priority_counts": dict(sorted(priority_counts.items())),
            "status_counts": dict(sorted(status_counts.items())),
        },
        "items": items,
        "report_only_items": report_only_items,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build archive source failure triage report.")
    parser.add_argument("--report", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, default=Path("conductor/archive_failure_triage_report.json"))
    args = parser.parse_args()

    report = build_report(args.report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {args.output} with {report['summary']['failure_count']} triage items.")


if __name__ == "__main__":
    main()






