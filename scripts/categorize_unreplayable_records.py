"""Scan X archive source records and identify those that cannot be replayed.

Categorises unreplayable records with standard reason codes:

    - empty_content:         Record has no text content (None, empty, whitespace-only)
    - exceeds_bluesky_limit: Content >2000 chars, beyond safe truncation to 300
    - media_only_no_text:    Has media/links but no meaningful text content
    - already_posted:        Record ID already posted to Bluesky mirror

Performs purely local file analysis; no live API access required.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

BLUESKY_MAX_CHARS: int = 300
EXCESSIVE_CONTENT_THRESHOLD: int = 2000

REASON_EMPTY_CONTENT: str = "empty_content"
REASON_EXCEEDS_LIMIT: str = "exceeds_bluesky_limit"
REASON_MEDIA_ONLY_NO_TEXT: str = "media_only_no_text"
REASON_ALREADY_POSTED: str = "already_posted"

REASON_CODES: set[str] = {
    REASON_EMPTY_CONTENT,
    REASON_EXCEEDS_LIMIT,
    REASON_MEDIA_ONLY_NO_TEXT,
    REASON_ALREADY_POSTED,
}


def load_posted_record_ids(state_path: Path) -> set[str]:
    """Load the set of already-posted record IDs from archive mirror state."""
    if not state_path.exists():
        return set()
    data = json.loads(state_path.read_text(encoding="utf-8"))
    posted_ids: set[str] = set()

    posted_by_source = data.get("posted_record_ids", {}).get("bluesky", {})
    for source_key, ids in posted_by_source.items():
        if isinstance(ids, list):
            posted_ids.update(str(rid) for rid in ids)
    return posted_ids


def scan_normalized_x_archive(
    archive_dir: Path,
) -> list[dict[str, Any]]:
    """Scan X JSONL files and return every record annotated with source file."""
    if not archive_dir.is_dir():
        return []

    records: list[dict[str, Any]] = []
    for jsonl_path in sorted(archive_dir.glob("*.jsonl")):
        for line in jsonl_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            record["_source_file"] = jsonl_path.relative_to(
                archive_dir.parent
            ).as_posix()
            records.append(record)
    return records


def classify_record(
    record: dict[str, Any],
    posted_ids: set[str],
) -> list[str]:
    """Return reason codes for why a record is unreplayable (empty = replayable)."""
    reasons: list[str] = []
    content = record.get("content")
    media_refs = record.get("media_refs", [])

    has_text = bool(content and content.strip())
    has_media = bool(media_refs)

    if not has_text and has_media:
        reasons.append(REASON_MEDIA_ONLY_NO_TEXT)
    elif not has_text:
        reasons.append(REASON_EMPTY_CONTENT)
    elif len(content.strip()) > EXCESSIVE_CONTENT_THRESHOLD:
        reasons.append(REASON_EXCEEDS_LIMIT)

    return reasons


def build_report(
    posted_ids: set[str],
    all_records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the unreplayable records report."""
    unreplayable: list[dict[str, Any]] = []
    posted_records: list[dict[str, Any]] = []
    replayable_count: int = 0
    already_posted_count: int = 0
    reason_counts: dict[str, int] = {code: 0 for code in REASON_CODES}

    for record in all_records:
        reasons = classify_record(record, posted_ids)
        record_id = str(record.get("record_id") or "")
        content = record.get("content") or ""
        if record_id in posted_ids:
            already_posted_count += 1
            posted_records.append(
                {
                    "record_id": record_id,
                    "source_file": record.get("_source_file", ""),
                    "source_url": str(record.get("source_url") or ""),
                    "original_created_at": str(
                        record.get("original_created_at") or ""
                    ),
                }
            )
            continue

        if reasons:
            entry: dict[str, Any] = {
                "record_id": record_id,
                "source_file": record.get("_source_file", ""),
                "source_url": str(record.get("source_url") or ""),
                "original_created_at": str(
                    record.get("original_created_at") or ""
                ),
                "content_preview": content[:120] if content else "",
                "content_length": len(content),
                "reasons": reasons,
            }
            unreplayable.append(entry)
            for code in reasons:
                reason_counts[code] = reason_counts.get(code, 0) + 1
        else:
            replayable_count += 1

    return {
        "report_version": "1.1",
        "total_records_scanned": len(all_records),
        "replayable": replayable_count,
        "unreplayable": len(unreplayable),
        "posted": already_posted_count,
        "already_posted": already_posted_count,
        "reason_counts": reason_counts,
        "posted_records": posted_records,
        "records": unreplayable,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Categorize unreplayable X archive records."
    )
    parser.add_argument(
        "--state-path",
        default="conductor/archive_mirror_state.json",
        help="Path to archive mirror state JSON",
    )
    parser.add_argument(
        "--normalized-x-dir",
        default="historical_archive_normalized/x",
        help="Directory containing normalized X archive JSONL files",
    )
    parser.add_argument(
        "--output",
        default="conductor/unreplayable_records_report.json",
        help="Path to write the unreplayable records report JSON",
    )
    args = parser.parse_args()

    state_path = Path(args.state_path)
    normalized_x_dir = Path(args.normalized_x_dir)
    output_path = Path(args.output)

    posted_ids = load_posted_record_ids(state_path)
    all_records = scan_normalized_x_archive(normalized_x_dir)
    report = build_report(posted_ids, all_records)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(
        f"Scanned {report['total_records_scanned']} records: "
        f"{report['replayable']} replayable, "
        f"{report['unreplayable']} unreplayable."
    )
    if report["unreplayable"] > 0:
        parts = [
            f"  {code}: {count}"
            for code, count in sorted(report["reason_counts"].items())
            if count > 0
        ]
        if parts:
            print("Reason breakdown:")
            print("\n".join(parts))
    print(f"Report written to {output_path}")


if __name__ == "__main__":
    main()
