from collections import defaultdict
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from src.archive_schema import NormalizedArchiveRecord


TRACKING_QUERY_PREFIXES = ("utm_",)
TRACKING_QUERY_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid", "ref", "ref_src"}


def canonical_dedupe_key(record: NormalizedArchiveRecord) -> str:
    canonical_url = normalize_canonical_url(record.get("canonical_url", ""))
    if canonical_url:
        return f"url:{canonical_url}"
    return f"hash:{record['content_hash']}"


def group_cross_source_records(
    records: list[NormalizedArchiveRecord],
) -> dict[str, list[NormalizedArchiveRecord]]:
    groups: dict[str, list[NormalizedArchiveRecord]] = defaultdict(list)
    for record in records:
        groups[canonical_dedupe_key(record)].append(record)
    return dict(sorted(groups.items()))


def cross_source_ids_for_group(records: list[NormalizedArchiveRecord]) -> dict[str, str]:
    ids: dict[str, str] = {}
    for record in sorted(records, key=lambda item: (item["source_platform"], item["record_id"])):
        ids[record["source_platform"]] = record["record_id"]
    return ids


def normalize_canonical_url(url: str) -> str:
    value = url.strip()
    if not value:
        return ""

    parsed = urlsplit(value)
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/") or "/"
    query_items = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not _is_tracking_query_key(key)
    ]
    query = urlencode(sorted(query_items), doseq=True)
    return urlunsplit((scheme, netloc, path, query, ""))


def _is_tracking_query_key(key: str) -> bool:
    lowered = key.lower()
    return lowered in TRACKING_QUERY_KEYS or any(
        lowered.startswith(prefix) for prefix in TRACKING_QUERY_PREFIXES
    )
