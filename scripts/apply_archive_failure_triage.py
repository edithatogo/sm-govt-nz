import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_MANIFEST = Path("conductor/govt_archive_source_manifest.json")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def recompute_summary(manifest: dict[str, Any]) -> None:
    counts = Counter(str(source.get("archive_status") or "unknown") for source in manifest.get("sources", []))
    manifest["generated_at"] = now_iso()
    manifest["summary"] = {
        "archive_status_counts": dict(sorted(counts.items())),
        "total_sources": len(manifest.get("sources", [])),
    }


def should_degrade(item: dict[str, Any]) -> bool:
    platform = item.get("platform")
    status = item.get("status")
    reason = str(item.get("reason") or "")
    if platform == "youtube":
        return status == "capture_failed" and (
            "not a channel URL" in reason
            or "not a YouTube URL" in reason
            or "HTTP Error 404" in reason
            or "control characters" in reason
        )
    if platform == "website_page":
        return status in {"capture_blocked", "dns_failed", "method_not_allowed", "not_acceptable", "not_found"}
    return False


def triage_note(item: dict[str, Any]) -> str:
    status = item.get("status", "unknown")
    reason = str(item.get("reason") or "").strip()
    if item.get("platform") == "youtube":
        return f"Archive triage {now_iso()[:10]}: degraded malformed, stale, or unreachable YouTube source after `{status}` ({reason}); keep out of default capture until a replacement channel URL is verified."
    return f"Archive triage {now_iso()[:10]}: degraded website source after `{status}` ({reason}); keep out of default capture until an alternate URL or access path is verified."


def apply_triage(manifest: dict[str, Any], triage_reports: list[dict[str, Any]]) -> dict[str, Any]:
    sources_by_id = {str(source.get("source_id")): source for source in manifest.get("sources", [])}
    changes = []
    for report in triage_reports:
        for item in report.get("items", []):
            if not isinstance(item, dict) or not should_degrade(item):
                continue
            source_id = str(item.get("source_id") or "")
            source = sources_by_id.get(source_id)
            if source is None:
                continue
            old_status = source.get("archive_status")
            old_feasibility = source.get("feasibility")
            note = triage_note(item)
            existing_notes = str(source.get("notes") or "")
            if note not in existing_notes:
                source["notes"] = f"{existing_notes} {note}".strip()
            source["archive_status"] = "degraded"
            source["feasibility"] = "low"
            source["updated_at"] = now_iso()
            changes.append(
                {
                    "source_id": source_id,
                    "platform": source.get("platform"),
                    "url": source.get("url"),
                    "old_archive_status": old_status,
                    "new_archive_status": source.get("archive_status"),
                    "old_feasibility": old_feasibility,
                    "new_feasibility": source.get("feasibility"),
                    "triage_status": item.get("status"),
                    "triage_reason": item.get("reason"),
                }
            )
    recompute_summary(manifest)
    return {
        "generated_at": now_iso(),
        "summary": {
            "changed_sources": len(changes),
            "platform_counts": dict(sorted(Counter(str(change.get("platform")) for change in changes).items())),
        },
        "changes": changes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply archive failure triage to the source manifest.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--triage-report", type=Path, action="append", required=True)
    parser.add_argument("--change-report", type=Path, default=Path("conductor/archive_failure_triage_manifest_updates.json"))
    args = parser.parse_args()

    manifest = load_json(args.manifest)
    triage_reports = [load_json(path) for path in args.triage_report]
    change_report = apply_triage(manifest, triage_reports)
    write_json(args.manifest, manifest)
    write_json(args.change_report, change_report)
    print(f"Applied archive failure triage to {change_report['summary']['changed_sources']} sources.")


if __name__ == "__main__":
    main()
