import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.archive_current_sources import archive_current_sources


DEFAULT_MANIFEST = Path("conductor/govt_archive_source_manifest.json")
DEFAULT_REPORT = Path("conductor/govt_archive_registered_sources_report.json")
SUPPORTED_PLATFORMS = {"rss", "website_page", "bluesky"}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def select_sources(
    sources: list[dict[str, Any]],
    agency_id: str,
    source_type: str,
    only_ready: bool,
) -> list[dict[str, Any]]:
    selected = []
    for source in sources:
        if agency_id and source.get("agency_id") != agency_id:
            continue
        if source_type != "all_feasible" and source.get("platform") != source_type and source.get("source_type") != source_type:
            continue
        if only_ready and source.get("archive_status") not in {"ready", "candidate"}:
            continue
        selected.append(source)
    return selected


def source_result(source: dict[str, Any], status: str, reason: str = "") -> dict[str, Any]:
    return {
        "source_id": source.get("source_id"),
        "agency_id": source.get("agency_id"),
        "platform": source.get("platform"),
        "source_type": source.get("source_type"),
        "url": source.get("url"),
        "archive_status": source.get("archive_status"),
        "feasibility": source.get("feasibility"),
        "status": status,
        "reason": reason,
    }


def run_courts_current_sources_if_selected(selected: list[dict[str, Any]], dry_run: bool) -> dict[str, Any] | None:
    courts_sources = [
        source
        for source in selected
        if source.get("agency_id") == "courts-nz" and source.get("platform") in SUPPORTED_PLATFORMS
    ]
    if not courts_sources:
        return None
    if dry_run:
        return {"dry_run": True, "selected_supported_courts_sources": len(courts_sources)}
    return archive_current_sources()


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_json(args.manifest)
    selected = select_sources(
        manifest.get("sources", []),
        agency_id=args.agency_id,
        source_type=args.source_type,
        only_ready=not args.include_blocked,
    )
    results = []
    courts_report = run_courts_current_sources_if_selected(selected, args.dry_run)
    for source in selected:
        platform = source.get("platform")
        if source.get("agency_id") == "courts-nz" and platform in SUPPORTED_PLATFORMS:
            results.append(source_result(source, "invoked", "handled by archive_current_sources.py"))
        elif platform in SUPPORTED_PLATFORMS:
            results.append(
                source_result(
                    source,
                    "pending_adapter",
                    "source is feasible but needs a generic adapter or source-specific config before capture",
                )
            )
        else:
            results.append(
                source_result(
                    source,
                    "unsupported_now",
                    "manifested for onboarding but not captured by the current archive runner",
                )
            )
    status_counts = Counter(row["status"] for row in results)
    return {
        "generated_at": now_iso(),
        "dry_run": args.dry_run,
        "inputs": {
            "manifest": str(args.manifest),
            "source_type": args.source_type,
            "agency_id": args.agency_id,
            "include_blocked": args.include_blocked,
        },
        "summary": {
            "selected_sources": len(selected),
            "status_counts": dict(sorted(status_counts.items())),
        },
        "courts_current_sources_report": courts_report,
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Invoke archive capture for registered government sources.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument(
        "--source-type",
        default="all_feasible",
        choices=["all_feasible", "rss", "website_page", "bluesky", "youtube", "facebook", "instagram", "threads", "linkedin", "x"],
    )
    parser.add_argument("--agency-id", default="")
    parser.add_argument("--include-blocked", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    report = build_report(args)
    write_json(args.report, report)
    print(
        "Archive registered sources report wrote "
        f"{report['summary']['selected_sources']} selected sources."
    )


if __name__ == "__main__":
    main()
