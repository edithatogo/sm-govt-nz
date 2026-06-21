"""Tests for scripts/categorize_unreplayable_records.py."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.categorize_unreplayable_records import (
    REASON_ALREADY_POSTED,
    REASON_EMPTY_CONTENT,
    REASON_EXCEEDS_LIMIT,
    REASON_MEDIA_ONLY_NO_TEXT,
    build_report,
    classify_record,
    load_posted_record_ids,
    scan_normalized_x_archive,
)


def _make_record(
    record_id: str = "x:100",
    content: str = "This is a normal replayable post.",
    media_refs: list | None = None,
) -> dict:
    return {
        "record_id": record_id,
        "source_platform": "x",
        "source_account": "CourtsofNZ",
        "content": content,
        "source_url": f"https://x.com/CourtsofNZ/status/{record_id.removeprefix('x:')}",
        "media_refs": media_refs or [],
        "original_created_at": "2024-01-15T00:00:00+00:00",
        "_source_file": "x/2024-01.jsonl",
    }


def _write_x_jsonl(archive_dir: Path, records: list[dict]) -> Path:
    """Write test records to a JSONL file in the given archive dir."""
    archive_dir.mkdir(parents=True, exist_ok=True)
    path = archive_dir / "2024-01.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")
    return path


# ---------------------------------------------------------------------------
# classify_record tests
# ---------------------------------------------------------------------------


def test_classify_replayable_record() -> None:
    """A normal record with text content should return no reasons."""
    record = _make_record()
    reasons = classify_record(record, posted_ids=set())
    assert reasons == []


def test_classify_empty_content() -> None:
    """A record with empty content should be marked empty_content."""
    record = _make_record(content="")
    reasons = classify_record(record, posted_ids=set())
    assert REASON_EMPTY_CONTENT in reasons
    assert REASON_MEDIA_ONLY_NO_TEXT not in reasons


def test_classify_none_content() -> None:
    """A record with None content should be marked empty_content."""
    record = _make_record(content=None)  # type: ignore[arg-type]
    reasons = classify_record(record, posted_ids=set())
    assert REASON_EMPTY_CONTENT in reasons


def test_classify_whitespace_only_content() -> None:
    """A record with whitespace-only content should be marked empty_content."""
    record = _make_record(content="   \n  \t  ")
    reasons = classify_record(record, posted_ids=set())
    assert REASON_EMPTY_CONTENT in reasons


def test_classify_media_only_no_text() -> None:
    """A record with media but no text should be media_only_no_text."""
    record = _make_record(
        content="",
        media_refs=[{"type": "photo", "url": "https://example.com/img.jpg"}],
    )
    reasons = classify_record(record, posted_ids=set())
    assert REASON_MEDIA_ONLY_NO_TEXT in reasons


def test_classify_exceeds_bluesky_limit() -> None:
    """A record with content over 2000 chars should be marked exceeds."""
    long_content = "x" * 2500
    record = _make_record(content=long_content)
    reasons = classify_record(record, posted_ids=set())
    assert REASON_EXCEEDS_LIMIT in reasons


def test_classify_under_threshold_is_replayable() -> None:
    """Content under 2000 chars but over 300 should still be replayable."""
    medium_content = "x" * 500
    record = _make_record(content=medium_content)
    reasons = classify_record(record, posted_ids=set())
    assert reasons == []


def test_classify_already_posted() -> None:
    """A record already posted should be marked already_posted."""
    record = _make_record(record_id="x:100")
    reasons = classify_record(record, posted_ids={"x:100"})
    assert REASON_ALREADY_POSTED in reasons


def test_classify_already_posted_and_empty() -> None:
    """A record both posted and empty should get both reasons."""
    record = _make_record(record_id="x:1", content="")
    reasons = classify_record(record, posted_ids={"x:1"})
    assert REASON_ALREADY_POSTED in reasons
    assert REASON_EMPTY_CONTENT in reasons


# ---------------------------------------------------------------------------
# load_posted_record_ids tests
# ---------------------------------------------------------------------------


def test_load_posted_ids_from_state(tmp_path: Path) -> None:
    """load_posted_record_ids extracts IDs from the state file."""
    state_path = tmp_path / "archive_mirror_state.json"
    state_path.write_text(
        json.dumps(
            {
                "posted_record_ids": {
                    "bluesky": {
                        "x:CourtsofNZ": ["x:100", "x:200", "x:300"],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    posted_ids = load_posted_record_ids(state_path)
    assert posted_ids == {"x:100", "x:200", "x:300"}


def test_load_posted_ids_missing_file(tmp_path: Path) -> None:
    """Missing state file should return empty set."""
    state_path = tmp_path / "nonexistent.json"
    posted_ids = load_posted_record_ids(state_path)
    assert posted_ids == set()


def test_load_posted_ids_empty_state(tmp_path: Path) -> None:
    """Empty state dict should return empty set."""
    state_path = tmp_path / "archive_mirror_state.json"
    state_path.write_text(json.dumps({}), encoding="utf-8")
    posted_ids = load_posted_record_ids(state_path)
    assert posted_ids == set()


# ---------------------------------------------------------------------------
# scan_normalized_x_archive tests
# ---------------------------------------------------------------------------


def test_scan_finds_records(tmp_path: Path) -> None:
    """scan_normalized_x_archive reads all JSONL records."""
    archive_dir = tmp_path / "historical_archive_normalized" / "x"
    _write_x_jsonl(
        archive_dir,
        [
            _make_record(record_id="x:1", content="First"),
            _make_record(record_id="x:2", content="Second"),
        ],
    )
    records = scan_normalized_x_archive(archive_dir)
    record_ids = [r["record_id"] for r in records]
    assert record_ids == ["x:1", "x:2"]
    assert all("_source_file" in r for r in records)


def test_scan_missing_dir(tmp_path: Path) -> None:
    """Non-existent directory should return an empty list."""
    records = scan_normalized_x_archive(tmp_path / "nonexistent")
    assert records == []


def test_scan_empty_dir(tmp_path: Path) -> None:
    """Empty directory should return an empty list."""
    archive_dir = tmp_path / "historical_archive_normalized" / "x"
    archive_dir.mkdir(parents=True)
    records = scan_normalized_x_archive(archive_dir)
    assert records == []


def test_scan_skips_invalid_json(tmp_path: Path) -> None:
    """Lines with invalid JSON should be silently skipped."""
    archive_dir = tmp_path / "historical_archive_normalized" / "x"
    archive_dir.mkdir(parents=True)
    path = archive_dir / "2024-01.jsonl"
    path.write_text(
        '{"record_id": "x:1", "content": "valid"}\n'
        "not-json-at-all\n"
        '{"record_id": "x:2", "content": "also valid"}\n',
        encoding="utf-8",
    )
    records = scan_normalized_x_archive(archive_dir)
    assert len(records) == 2


# ---------------------------------------------------------------------------
# build_report integration tests
# ---------------------------------------------------------------------------


def test_report_all_replayable() -> None:
    """Report shows zero unreplayable when all records are fine."""
    records = [
        _make_record(record_id="x:1", content="First post."),
        _make_record(record_id="x:2", content="Second post."),
    ]
    report = build_report(posted_ids=set(), all_records=records)
    assert report["total_records_scanned"] == 2
    assert report["replayable"] == 2
    assert report["unreplayable"] == 0
    assert report["records"] == []


def test_report_categorizes_unreplayable() -> None:
    """Report correctly classifies various unreplayable records."""
    records = [
        _make_record(record_id="x:1", content="Good"),
        _make_record(record_id="x:2", content=""),
        _make_record(record_id="x:3", content="x" * 2500),
        _make_record(
            record_id="x:4", content="", media_refs=[{"type": "photo"}]
        ),
        _make_record(record_id="x:5", content="Already done"),
    ]
    report = build_report(posted_ids={"x:5"}, all_records=records)
    assert report["total_records_scanned"] == 5
    assert report["replayable"] == 1  # only x:1 is fully replayable
    assert report["unreplayable"] == 4

    reported_ids = {r["record_id"] for r in report["records"]}
    assert reported_ids == {"x:2", "x:3", "x:4", "x:5"}

    assert report["reason_counts"]["empty_content"] == 1
    assert report["reason_counts"]["exceeds_bluesky_limit"] == 1
    assert report["reason_counts"]["media_only_no_text"] == 1
    assert report["reason_counts"]["already_posted"] == 1


def test_report_output_format() -> None:
    """Report contains all expected top-level keys and record fields."""
    records = [_make_record(record_id="x:1", content="")]
    report = build_report(posted_ids=set(), all_records=records)

    assert "report_version" in report
    assert "total_records_scanned" in report
    assert "replayable" in report
    assert "unreplayable" in report
    assert "reason_counts" in report
    assert "records" in report

    for code in (
        REASON_EMPTY_CONTENT,
        REASON_EXCEEDS_LIMIT,
        REASON_MEDIA_ONLY_NO_TEXT,
        REASON_ALREADY_POSTED,
    ):
        assert code in report["reason_counts"]

    assert len(report["records"]) == 1
    entry = report["records"][0]
    assert "record_id" in entry
    assert "source_file" in entry
    assert "source_url" in entry
    assert "original_created_at" in entry
    assert "content_preview" in entry
    assert "content_length" in entry
    assert "reasons" in entry


def test_report_includes_already_posted_count() -> None:
    """Report separates already_posted from other unreplayable records."""
    records = [
        _make_record(record_id="x:1", content="Posted"),
        _make_record(record_id="x:2", content=""),
        _make_record(record_id="x:3", content="Pending"),
    ]
    report = build_report(posted_ids={"x:1"}, all_records=records)

    assert report["already_posted"] == 1
    assert report["replayable"] == 1
    assert report["unreplayable"] == 2
