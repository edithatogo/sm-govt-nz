import argparse
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.register_archive_source import load_manifest, upsert_source, write_manifest  # noqa: E402


DEFAULT_REPORT = Path("conductor/govt_source_candidate_report.json")
DEFAULT_MANIFEST = Path("conductor/govt_archive_source_manifest.json")
DEFAULT_SUMMARY = Path("conductor/govt_definite_public_source_promotion_summary.json")
DEFAULT_MIN_CONFIDENCE = 0.6
GOVERNMENT_SUFFIXES = (".govt.nz", ".mil.nz", ".parliament.nz")
PUBLIC_SOURCE_TYPES = {"rss_feed", "json_feed", "website_page"}


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def host_from_url(url: str) -> str:
    parsed = urlparse(url)
    return (parsed.hostname or "").lower()


def is_definite_government_website(url: str) -> bool:
    host = host_from_url(url)
    return any(host.endswith(suffix) for suffix in GOVERNMENT_SUFFIXES)


def select_candidates(report: dict[str, Any], min_confidence: float) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for item in report.get("candidates", []):
        source_type = str(item.get("source_type") or "")
        if source_type not in PUBLIC_SOURCE_TYPES:
            continue
        if str(item.get("archive_status") or "") != "ready":
            continue
        if str(item.get("status") or "") not in {"active", "discovered"}:
            continue
        if float(item.get("confidence_score", 0)) < min_confidence:
            continue
        if source_type == "website_page" and not is_definite_government_website(str(item.get("url") or "")):
            continue
        selected.append(item)
    return sorted(
        selected,
        key=lambda row: (
            str(row.get("source_type", "")),
            str(row.get("agency_id", "")),
            str(row.get("url", "")),
        ),
    )


def promote_candidates(
    report: dict[str, Any],
    manifest_path: Path,
    min_confidence: float,
) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    selected = select_candidates(report, min_confidence)
    added = 0
    updated = 0
    by_type: dict[str, int] = {}
    manifest_json_feed_count = sum(1 for source in manifest.get("sources", []) if str(source.get("source_type") or "") == "json_feed")

    for item in selected:
        source_type = str(item.get("source_type") or "")
        source = {
            "source_id": item["candidate_id"],
            "agency_id": item["agency_id"],
            "agency_name": item.get("agency_name", ""),
            "source_type": source_type,
            "platform": item.get("platform", source_type),
            "url": item["url"],
            "account": item.get("account", ""),
            "feasibility": item.get("feasibility", "high"),
            "archive_status": "ready",
            "access_method": item.get("access_method", "public"),
            "auth": item.get("auth", "none"),
            "origin": item.get("origin", "govt_source_discovery"),
            "notes": (
                f"Promoted as definite public source: confidence={item.get('confidence_score', '')}; "
                f"type={source_type}"
            ).strip(),
        }
        outcome = upsert_source(manifest, source)
        if outcome == "added":
            added += 1
        else:
            updated += 1
        by_type[source_type] = by_type.get(source_type, 0) + 1

    write_manifest(manifest_path, manifest)
    summary = {
        "selected_count": len(selected),
        "added_count": added,
        "updated_count": updated,
        "manifest_json_feed_count": manifest_json_feed_count,
        "min_confidence": min_confidence,
        "selected_source_types": sorted(by_type),
        "selected_counts_by_type": dict(sorted(by_type.items())),
        "government_suffixes": list(GOVERNMENT_SUFFIXES),
    }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Promote definite public source candidates into the archive manifest.")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=DEFAULT_MIN_CONFIDENCE,
        help="Minimum confidence score required for promotion.",
    )
    args = parser.parse_args()

    report = load_json(args.report)
    summary = promote_candidates(report, args.manifest, args.min_confidence)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
