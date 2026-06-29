import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


DEFAULT_MANIFEST = Path("conductor/govt_archive_source_manifest.json")
DEFAULT_SEED_ROOT = Path("manual_archive_seeds/threads")
DEFAULT_VALIDATION = Path("conductor/threads_manual_seed_validation_report.json")
DEFAULT_REPORT = Path("conductor/threads_seed_readiness_report.json")
DEFAULT_SUMMARY = Path("conductor/threads_seed_readiness_summary.md")


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _handle_from_threads_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if path.startswith("@"):
        return path.split("/", 1)[0].removeprefix("@").lower()
    return ""


def _validation_by_path(validation: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("path") or "").replace("\\", "/"): item
        for item in validation.get("results", [])
        if item.get("path")
    }


def _seed_candidates(source: dict[str, Any], seed_root: Path) -> list[str]:
    source_id = str(source.get("source_id") or "")
    agency_id = str(source.get("agency_id") or "")
    candidates = []
    if source_id:
        candidates.append(str(seed_root / f"{source_id}.json").replace("\\", "/"))
    if agency_id:
        candidates.append(str(seed_root / f"{agency_id}.json").replace("\\", "/"))
    return candidates


def _item(source: dict[str, Any], seed_root: Path, validation_index: dict[str, dict[str, Any]]) -> dict[str, Any]:
    candidates = _seed_candidates(source, seed_root)
    present = [candidate for candidate in candidates if Path(candidate).is_file()]
    validation_results = [validation_index[candidate] for candidate in present if candidate in validation_index]
    invalid = [result for result in validation_results if result.get("status") == "invalid"]
    records = sum(int(result.get("record_count") or 0) for result in validation_results)
    if invalid:
        readiness = "seed_invalid"
    elif records:
        readiness = "ready_to_archive"
    elif present:
        readiness = "seed_empty"
    else:
        readiness = "seed_missing"
    return {
        "source_id": source.get("source_id", ""),
        "agency_id": source.get("agency_id", ""),
        "agency_name": source.get("agency_name", ""),
        "url": source.get("url", ""),
        "handle": _handle_from_threads_url(str(source.get("url") or "")),
        "archive_status": source.get("archive_status", ""),
        "feasibility": source.get("feasibility", ""),
        "access_method": source.get("access_method", ""),
        "seed_candidates": candidates,
        "seed_files_present": present,
        "validation_results": validation_results,
        "record_count": records,
        "readiness": readiness,
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    manifest = _load_json(args.manifest, {})
    validation = _load_json(args.validation_report, {"results": []})
    validation_index = _validation_by_path(validation)
    sources = [
        source for source in manifest.get("sources", [])
        if source.get("platform") == "threads" or source.get("source_type") == "threads"
    ]
    items = [_item(source, args.seed_root, validation_index) for source in sources]
    readiness_counts = Counter(item["readiness"] for item in items)
    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "description": "Readiness report for registered Threads sources using approved API access or operator-authorized manual seed exports.",
        "inputs": {
            "manifest": str(args.manifest),
            "seed_root": str(args.seed_root),
            "validation_report": str(args.validation_report),
        },
        "summary": {
            "registered_threads_sources": len(items),
            "readiness_counts": dict(sorted(readiness_counts.items())),
            "records_ready": sum(int(item.get("record_count") or 0) for item in items),
            "seed_files_present": sum(1 for item in items if item.get("seed_files_present")),
        },
        "items": sorted(items, key=lambda item: (item["agency_id"], item["source_id"])),
    }


def write_summary(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# Threads Seed Readiness",
        "",
        f"Generated: {report.get('generated_at', '')}",
        "",
        "## Summary",
        "",
    ]
    for key, value in report.get("summary", {}).items():
        lines.append(f"- `{key}`: {value}")
    lines.extend([
        "",
        "## Registered Threads sources",
        "",
        "| Source | Agency | Handle | Readiness | Records | Seed candidates |",
        "| --- | --- | --- | --- | ---: | --- |",
    ])
    for item in report.get("items", []):
        candidates = "<br>".join(f"`{candidate}`" for candidate in item.get("seed_candidates", []))
        lines.append(
            "| {source_id} | {agency_id} | @{handle} | {readiness} | {records} | {candidates} |".format(
                source_id=item.get("source_id", ""),
                agency_id=item.get("agency_id", ""),
                handle=item.get("handle", ""),
                readiness=item.get("readiness", ""),
                records=item.get("record_count", 0),
                candidates=candidates,
            )
        )
    lines.extend([
        "",
        "## Operator next step",
        "",
        "Add authorized seed JSON files for `seed_missing` sources, then run `Validate Threads Manual Seeds` followed by `Archive Threads Manual Seeds`.",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Threads manual seed readiness report.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--seed-root", type=Path, default=DEFAULT_SEED_ROOT)
    parser.add_argument("--validation-report", type=Path, default=DEFAULT_VALIDATION)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    args = parser.parse_args()
    report = build_report(args)
    _write_json(args.report, report)
    write_summary(args.summary, report)
    print(
        "Threads seed readiness report wrote "
        f"{report['summary']['registered_threads_sources']} registered sources."
    )


if __name__ == "__main__":
    main()
