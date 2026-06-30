import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_NORMALIZED_ROOT = Path("historical_archive_normalized")
DEFAULT_STATUS_REPORT = Path("conductor/archive_publication_status.json")
DEFAULT_LEDGER = Path("conductor/monthly_release_ledger.json")
DEFAULT_OUTPUT = Path("conductor/monthly_release_plan.json")
DEFAULT_SUMMARY = Path("conductor/monthly_release_plan.md")
MONTH_RE = re.compile(r"^\d{4}-\d{2}$")


def _load_status(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _iter_normalized_records(root: Path) -> list[tuple[str, dict[str, Any]]]:
    records: list[tuple[str, dict[str, Any]]] = []
    if not root.exists():
        return records
    for path in sorted(root.glob("*/*.jsonl")):
        if not path.is_file():
            continue
        source = path.parent.name
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL in {path}:{line_number}") from exc
            records.append((source, payload))
    return records


def _record_month(record: dict[str, Any], fallback_source_month: str = "") -> str:
    value = str(record.get("original_created_at") or record.get("captured_at") or "")
    match = re.search(r"(\d{4}-\d{2})", value)
    if match:
        return match.group(1)
    return fallback_source_month if MONTH_RE.match(fallback_source_month) else "unknown"


def _published_versions(status_report: Path, ledger_path: Path) -> set[str]:
    versions: set[str] = set()
    status = _load_status(status_report)
    if status.get("mode") == "published" and str(status.get("release_version") or ""):
        versions.add(str(status.get("release_version")))
    ledger = _load_status(ledger_path)
    for release in ledger.get("releases", []):
        if release.get("mode") == "published" and str(release.get("release_version") or ""):
            versions.add(str(release.get("release_version")))
    return versions


def build_plan(normalized_root: Path, status_report: Path, ledger_path: Path = DEFAULT_LEDGER) -> dict[str, Any]:
    records = _iter_normalized_records(normalized_root)
    published_versions = _published_versions(status_report, ledger_path)
    by_month: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "record_count": 0,
            "source_counts": Counter(),
            "accounts": set(),
        }
    )
    for source, record in records:
        month = _record_month(record)
        item = by_month[month]
        item["record_count"] += 1
        item["source_counts"][str(record.get("source_platform") or source or "unknown")] += 1
        account = str(record.get("source_account") or "")
        if account:
            item["accounts"].add(account)
    months = []
    for month, item in sorted(by_month.items()):
        months.append(
            {
                "month": month,
                "release_version": month,
                "record_count": item["record_count"],
                "source_counts": dict(sorted(item["source_counts"].items())),
                "account_count": len(item["accounts"]),
                "status": "published" if month in published_versions else "candidate",
                "publish_command": (
                    "gh workflow run \"Publish Archives\" --ref master "
                    f"-f publish=true -f publication_target=all -f archive_release_version={month} "
                    "-f hf_dataset_name=corpus-social-media-government-nz "
                    "-f zenodo_deposit_api_url=https://zenodo.org/api/deposit/depositions"
                ),
            }
        )
    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "description": "Cumulative monthly release plan. Each release bundles all archived accounts and sources present in the repository at release time.",
        "published_release_versions": sorted(published_versions),
        "summary": {
            "months_with_records": len(months),
            "total_records": sum(item["record_count"] for item in months),
            "published_months": sum(1 for item in months if item["status"] == "published"),
            "candidate_months": sum(1 for item in months if item["status"] == "candidate"),
        },
        "months": months,
    }


def write_summary(path: Path, plan: dict[str, Any]) -> None:
    lines = [
        "# Monthly Release Plan",
        "",
        f"Generated: {plan.get('generated_at', '')}",
        "",
        "Each monthly release is cumulative: it bundles all archived accounts and source types present in the repository at release time.",
        "",
        "## Summary",
        "",
    ]
    for key, value in plan.get("summary", {}).items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Months", "", "| Month | Status | Records | Accounts | Sources |", "| --- | --- | ---: | ---: | --- |"])
    for item in plan.get("months", []):
        sources = ", ".join(f"{key}: {value}" for key, value in item.get("source_counts", {}).items())
        lines.append(
            f"| {item['month']} | {item['status']} | {item['record_count']} | {item['account_count']} | {sources} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build cumulative monthly archive release plan.")
    parser.add_argument("--normalized-root", type=Path, default=DEFAULT_NORMALIZED_ROOT)
    parser.add_argument("--status-report", type=Path, default=DEFAULT_STATUS_REPORT)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    args = parser.parse_args()
    plan = build_plan(args.normalized_root, args.status_report, args.ledger)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_summary(args.summary, plan)
    print(
        "Monthly release plan wrote "
        f"{plan['summary']['months_with_records']} months and {plan['summary']['total_records']} records."
    )


if __name__ == "__main__":
    main()
