import hashlib
import json
from typing import Any, TypedDict


class MediaReference(TypedDict, total=False):
    url: str
    media_type: str
    alt_text: str
    raw_path: str
    sha256: str


class NormalizedArchiveRecord(TypedDict):
    record_id: str
    agency_id: str
    source_platform: str
    source_account: str
    source_kind: str
    source_url: str
    canonical_url: str
    original_created_at: str
    captured_at: str
    content: str
    content_hash: str
    raw_path: str
    media_refs: list[MediaReference]
    extraction_method: str
    cross_source_ids: dict[str, str]


REQUIRED_NORMALIZED_FIELDS = {
    "record_id",
    "agency_id",
    "source_platform",
    "source_account",
    "source_kind",
    "source_url",
    "canonical_url",
    "original_created_at",
    "captured_at",
    "content",
    "content_hash",
    "raw_path",
    "media_refs",
    "extraction_method",
    "cross_source_ids",
}


def build_normalized_record(
    *,
    record_id: str,
    agency_id: str,
    source_platform: str,
    source_account: str,
    source_kind: str,
    source_url: str,
    canonical_url: str,
    original_created_at: str,
    captured_at: str,
    content: str,
    raw_path: str,
    extraction_method: str,
    media_refs: list[MediaReference] | None = None,
    cross_source_ids: dict[str, str] | None = None,
) -> NormalizedArchiveRecord:
    record: NormalizedArchiveRecord = {
        "record_id": record_id,
        "agency_id": agency_id,
        "source_platform": source_platform,
        "source_account": source_account,
        "source_kind": source_kind,
        "source_url": source_url,
        "canonical_url": canonical_url,
        "original_created_at": original_created_at,
        "captured_at": captured_at,
        "content": content,
        "content_hash": compute_content_hash(
            content=content,
            canonical_url=canonical_url,
            media_refs=media_refs or [],
        ),
        "raw_path": raw_path,
        "media_refs": media_refs or [],
        "extraction_method": extraction_method,
        "cross_source_ids": cross_source_ids or {},
    }
    validate_normalized_record(record)
    return record


def compute_content_hash(
    *,
    content: str,
    canonical_url: str = "",
    media_refs: list[MediaReference] | None = None,
) -> str:
    media_urls = sorted(str(item.get("url", "")) for item in media_refs or [] if item.get("url"))
    payload = {
        "canonical_url": canonical_url.strip(),
        "content": _normalize_text(content),
        "media_urls": media_urls,
    }
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def validate_normalized_record(record: dict[str, Any]) -> None:
    missing = REQUIRED_NORMALIZED_FIELDS - set(record)
    if missing:
        raise ValueError(f"Normalized archive record missing fields: {', '.join(sorted(missing))}")

    for field in REQUIRED_NORMALIZED_FIELDS - {"media_refs", "cross_source_ids"}:
        if not isinstance(record[field], str):
            raise ValueError(f"Normalized archive record field must be a string: {field}")

    if not isinstance(record["media_refs"], list):
        raise ValueError("Normalized archive record media_refs must be a list.")
    if not isinstance(record["cross_source_ids"], dict):
        raise ValueError("Normalized archive record cross_source_ids must be an object.")
    if record["content_hash"] != compute_content_hash(
        content=str(record["content"]),
        canonical_url=str(record["canonical_url"]),
        media_refs=record["media_refs"],
    ):
        raise ValueError("Normalized archive record content_hash does not match content.")


def _normalize_text(value: str) -> str:
    return " ".join(value.replace("\r", "\n").split())
