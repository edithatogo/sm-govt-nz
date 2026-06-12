import pytest

from src.archive_schema import (
    build_normalized_record,
    compute_content_hash,
    validate_normalized_record,
)


def test_build_normalized_record_adds_stable_content_hash():
    media_refs = [{"url": "https://example.test/image.jpg", "media_type": "image"}]

    record = build_normalized_record(
        record_id="rss:123",
        agency_id="courts-nz",
        source_platform="rss",
        source_account="courtsofnz.govt.nz",
        source_kind="rss_entry",
        source_url="https://example.test/feed",
        canonical_url="https://example.test/judgment",
        original_created_at="2026-06-12T00:00:00+00:00",
        captured_at="2026-06-12T01:00:00+00:00",
        content="  Judgment   published\n",
        raw_path="historical_archive_raw/rss/2026-06/rss-123.json",
        media_refs=media_refs,
        extraction_method="feedparser",
        cross_source_ids={"feed_entry_id": "123"},
    )

    assert record["content_hash"] == compute_content_hash(
        content="Judgment published",
        canonical_url="https://example.test/judgment",
        media_refs=media_refs,
    )
    assert record["cross_source_ids"]["feed_entry_id"] == "123"


def test_validate_normalized_record_rejects_missing_required_field():
    record = build_normalized_record(
        record_id="rss:123",
        agency_id="courts-nz",
        source_platform="rss",
        source_account="courtsofnz.govt.nz",
        source_kind="rss_entry",
        source_url="https://example.test/feed",
        canonical_url="https://example.test/judgment",
        original_created_at="2026-06-12T00:00:00+00:00",
        captured_at="2026-06-12T01:00:00+00:00",
        content="Judgment published",
        raw_path="historical_archive_raw/rss/2026-06/rss-123.json",
        extraction_method="feedparser",
    )
    del record["raw_path"]

    with pytest.raises(ValueError, match="missing fields"):
        validate_normalized_record(record)


def test_validate_normalized_record_rejects_mismatched_hash():
    record = build_normalized_record(
        record_id="rss:123",
        agency_id="courts-nz",
        source_platform="rss",
        source_account="courtsofnz.govt.nz",
        source_kind="rss_entry",
        source_url="https://example.test/feed",
        canonical_url="https://example.test/judgment",
        original_created_at="2026-06-12T00:00:00+00:00",
        captured_at="2026-06-12T01:00:00+00:00",
        content="Judgment published",
        raw_path="historical_archive_raw/rss/2026-06/rss-123.json",
        extraction_method="feedparser",
    )
    record["content_hash"] = "bad"

    with pytest.raises(ValueError, match="content_hash"):
        validate_normalized_record(record)
