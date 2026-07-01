import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SUCCESS_STATUSES = {"captured", "already_captured", "would_capture", "manual_seed_captured"}

ACTION_BY_STATUS = {
    "capture_blocked": "review_access_or_mark_blocked",
    "capture_failed": "review_url_or_adapter",
    "dns_failed": "verify_url_or_mark_stale",
    "method_not_allowed": "review_alternate_url",
    "network_error": "retry_later",
    "no_records": "monitor_or_verify_channel_activity",
    "not_acceptable": "review_headers_or_alternate_url",
    "tls_failed": "review_tls_or_alternate_url",
}

def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def triage_item(report_path: Path, row: dict[str, Any]) -> dict[str, Any]:
    status = str(row.get("status") or "unknown")
    source_id = str(row.get("source_id") or "")
    platform = str(row.get("platform") or "")
    agency_id = str(row.get("agency_id") or "")
    url = str(row.get("url") or "")
    reason = str(row.get("reason") or "")
    return {
        "source_id": source_id,
        "agency_id": agency_id,
        "platform": platform,
        "url": url,
        "status": status,
        "reason": reason,
        "recommended_action": ACTION_BY_STATUS.get(status, "review"),
        "report": str(report_path),
    }


def build_report(report_paths: list[Path]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
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
            if row.get("status") not in SUCCESS_STATUSES:
                items.append(triage_item(report_path, row))
    status_counts = Counter(item["status"] for item in items)
    platform_counts = Counter(item["platform"] for item in items)
    return {
        "generated_at": now_iso(),
        "inputs": {"reports": [str(path) for path in report_paths]},
        "report_summaries": report_summaries,
        "summary": {
            "failure_count": len(items),
            "platform_counts": dict(sorted(platform_counts.items())),
            "status_counts": dict(sorted(status_counts.items())),
        },
        "items": items,
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
