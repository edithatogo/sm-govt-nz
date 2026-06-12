from src.archive_dedupe import (
    canonical_dedupe_key,
    cross_source_ids_for_group,
    group_cross_source_records,
    normalize_canonical_url,
)
from src.archive_schema import build_normalized_record


def _record(record_id: str, platform: str, canonical_url: str, content: str = "content"):
    return build_normalized_record(
        record_id=record_id,
        agency_id="courts-nz",
        source_platform=platform,
        source_account=platform,
        source_kind="test",
        source_url=canonical_url or f"https://example.test/{record_id}",
        canonical_url=canonical_url,
        original_created_at="2026-06-12T00:00:00+00:00",
        captured_at="2026-06-12T01:00:00+00:00",
        content=content,
        raw_path=f"historical_archive_raw/{platform}/2026-06/{record_id}.json",
        extraction_method="test",
    )


def test_normalize_canonical_url_removes_tracking_query_and_fragment():
    assert (
        normalize_canonical_url("HTTPS://Example.Test/Judgment/?utm_source=x&b=2&a=1#section")
        == "https://example.test/Judgment?a=1&b=2"
    )


def test_canonical_dedupe_key_prefers_canonical_url():
    record = _record("rss-1", "rss", "https://example.test/judgment?utm_source=rss")

    assert canonical_dedupe_key(record) == "url:https://example.test/judgment"


def test_canonical_dedupe_key_falls_back_to_content_hash():
    record = _record("email-1", "email", "", content="same notice")

    assert canonical_dedupe_key(record) == f"hash:{record['content_hash']}"


def test_group_cross_source_records_groups_by_canonical_url():
    rss = _record("rss-1", "rss", "https://example.test/judgment?utm_source=rss")
    email = _record("email-1", "email", "https://example.test/judgment")
    bluesky = _record("bsky-1", "bluesky", "https://example.test/other")

    groups = group_cross_source_records([rss, email, bluesky])

    assert len(groups) == 2
    assert [record["record_id"] for record in groups["url:https://example.test/judgment"]] == [
        "rss-1",
        "email-1",
    ]
    assert cross_source_ids_for_group(groups["url:https://example.test/judgment"]) == {
        "email": "email-1",
        "rss": "rss-1",
    }
