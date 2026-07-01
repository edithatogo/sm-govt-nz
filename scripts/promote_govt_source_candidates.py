import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.discover_govt_source_candidates import looks_like_public_newsletter_archive  # noqa: E402
from scripts.register_archive_source import load_manifest, upsert_source, write_manifest  # noqa: E402


DEFAULT_REPORT = Path("conductor/govt_source_candidate_report.json")
DEFAULT_MANIFEST = Path("conductor/govt_archive_source_manifest.json")
DEFAULT_ALLOWED_SOURCE_TYPES = ("rss_feed", "json_feed", "api_endpoint", "website_page", "newsletter", "social_profile")
DEFAULT_MIN_CONFIDENCE = 0.6


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def select_candidates(
    report: dict[str, Any],
    allowed_source_types: set[str],
    min_confidence: float,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for item in report.get("candidates", []):
        if item.get("source_type") not in allowed_source_types:
            continue
        if item.get("source_type") == "social_profile":
            origin = str(item.get("origin", ""))
            if "registry.social_profiles" not in origin:
                continue
            if item.get("status") != "active":
                continue
            if "registry_known" not in set(item.get("trust_signals", [])):
                continue
        if item.get("source_type") == "newsletter" and not looks_like_public_newsletter_archive(
            str(item.get("url", "")),
            str(item.get("link_text", "")),
        ):
            continue
        if item.get("source_type") != "social_profile" and item.get("archive_status") != "ready":
            continue
        if float(item.get("confidence_score", 0)) < min_confidence:
            continue
        if item.get("status") not in {"active", "discovered"}:
            continue
        selected.append(item)
    return sorted(
        selected,
        key=lambda row: (
            -float(row.get("confidence_score", 0)),
            str(row.get("source_type", "")),
            str(row.get("agency_id", "")),
            str(row.get("url", "")),
        ),
    )


def register_selected_candidates(
    report: dict[str, Any],
    manifest_path: Path,
    allowed_source_types: set[str],
    min_confidence: float,
) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    selected = select_candidates(report, allowed_source_types, min_confidence)
    added = 0
    updated = 0

    for item in selected:
        source = {
            "source_id": item["candidate_id"],
            "agency_id": item["agency_id"],
            "agency_name": item.get("agency_name", ""),
            "source_type": item["source_type"],
            "platform": item.get("platform", item["source_type"]),
            "url": item["url"],
            "account": item.get("account", ""),
            "feasibility": item.get("feasibility", "review_required"),
            "archive_status": "ready" if item.get("source_type") == "social_profile" else item.get("archive_status", "candidate"),
            "access_method": item.get("access_method", "review_required"),
            "auth": item.get("auth", "review_required"),
            "origin": item.get("origin", "govt_source_discovery"),
            "notes": (
                f"Promoted from discovery: confidence={item.get('confidence_score', '')}; "
                f"trust={','.join(item.get('trust_signals', []))}"
            ).strip(),
        }
        outcome = upsert_source(manifest, source)
        if outcome == "added":
            added += 1
        else:
            updated += 1

    write_manifest(manifest_path, manifest)
    return {
        "selected_count": len(selected),
        "added_count": added,
        "updated_count": updated,
        "selected_source_types": sorted(allowed_source_types),
        "min_confidence": min_confidence,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Promote discovered government source candidates into the archive manifest.")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--allowed-source-types",
        default=",".join(DEFAULT_ALLOWED_SOURCE_TYPES),
        help="Comma-separated source types eligible for automatic promotion.",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=DEFAULT_MIN_CONFIDENCE,
        help="Minimum confidence score required for automatic promotion.",
    )
    args = parser.parse_args()

    report = load_json(args.report)
    allowed_source_types = {item.strip() for item in args.allowed_source_types.split(",") if item.strip()}
    result = register_selected_candidates(report, args.manifest, allowed_source_types, args.min_confidence)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
