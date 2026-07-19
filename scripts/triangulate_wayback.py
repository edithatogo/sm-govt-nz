"""Collect compact Internet Archive CDX evidence for registered sources.

This is corroboration metadata only. It does not download or republish archived
snapshots and never writes to the Internet Archive.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MATRIX = ROOT / "conductor/archive_completion_matrix.json"
DEFAULT_OUTPUT = ROOT / "conductor/archive_triangulation_wayback.json"
WAYBACK_CDX = "https://web.archive.org/cdx/search/cdx"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def query_wayback(url: str, *, timeout: int = 30, opener=urlopen) -> list[dict[str, str]]:
    params = {
        "url": url,
        "output": "json",
        "fl": "timestamp,original,statuscode,mimetype,digest",
        "filter": ["statuscode:200", "mimetype:text/html"],
        "collapse": "digest",
        "limit": "20",
    }
    query = urlencode(params, doseq=True)
    request = Request(
        f"{WAYBACK_CDX}?{query}",
        headers={"User-Agent": "sm-govt-nz/wayback-triangulation (+https://github.com/edithatogo/sm-govt-nz)"},
    )
    with opener(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not payload:
        return []
    headers, *rows = payload
    return [dict(zip(headers, row, strict=False)) for row in rows if isinstance(row, list)]


def is_transient(exc: Exception) -> bool:
    code = getattr(exc, "code", None)
    return isinstance(exc, (TimeoutError, URLError)) or code in {408, 425, 429, 500, 502, 503, 504}


def with_retries(operation, *, retries: int = 3, backoff: float = 1.0, max_backoff: float = 30.0):
    attempts = max(1, retries)
    for attempt in range(attempts):
        try:
            return operation()
        except Exception as exc:
            if attempt + 1 >= attempts or not is_transient(exc):
                raise
            time.sleep(min(max_backoff, backoff * (2**attempt)))


def select_sources(sources: list[dict], *, limit: int, offset: int, shard_index: int, shard_count: int) -> list[dict]:
    eligible = []
    for source in sources:
        key = str(source.get("source_id") or source.get("url") or "")
        digest = int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "big")
        if digest % shard_count == shard_index:
            eligible.append(source)
    return eligible[offset : offset + limit]


def merge_report(existing: dict | None, selected: list[dict], *, metadata: dict) -> dict:
    prior = {str(row.get("source_id")): row for row in (existing or {}).get("sources", []) if row.get("source_id")}
    prior.update({str(row.get("source_id")): row for row in selected if row.get("source_id")})
    rows = list(prior.values())
    return {**metadata, "sources": rows}


def triangulate(matrix: dict, *, limit: int = 100, offset: int = 0, shard_index: int = 0,
               shard_count: int = 1, delay: float = 0.25, retries: int = 3,
               backoff: float = 1.0, existing_report: dict | None = None) -> dict:
    if shard_count < 1 or not 0 <= shard_index < shard_count:
        raise ValueError("shard_index must be within shard_count")
    sources = matrix.get("sources") or []
    rows: list[dict] = []
    selected_sources = select_sources(sources, limit=max(0, limit), offset=max(0, offset),
                                      shard_index=shard_index, shard_count=shard_count)
    for source in selected_sources:
        url = str(source.get("url") or "")
        result: dict = {
            "source_id": source.get("source_id"),
            "platform": source.get("platform"),
            "url": url,
            "wayback_status": "not_checked",
            "capture_count": 0,
            "captures": [],
        }
        if not url.startswith(("http://", "https://")):
            result["wayback_status"] = "unsupported_url"
        else:
            try:
                captures = with_retries(lambda: query_wayback(url), retries=retries, backoff=backoff)
                result["captures"] = captures
                result["capture_count"] = len(captures)
                result["wayback_status"] = "capture_metadata_found" if captures else "no_capture_found"
            except Exception as exc:  # network/provider failures are reportable per source
                result["wayback_status"] = "provider_error"
                result["error"] = f"{type(exc).__name__}: {exc}"
        rows.append(result)
        if delay:
            time.sleep(delay)
    metadata = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "matrix_revision": os.environ.get("GITHUB_SHA"),
        "provider": "internet_archive_wayback_cdx",
        "purpose": "independent historical corroboration metadata; not canonical capture",
        "snapshot_downloaded": False,
        "source_limit": limit,
        "batch": {"offset": max(0, offset), "shard_index": shard_index, "shard_count": shard_count,
                  "selected_sources": len(rows)},
        "summary": {
            "sources_checked": len(rows),
            "capture_metadata_sources": sum(r["wayback_status"] == "capture_metadata_found" for r in rows),
            "no_capture_sources": sum(r["wayback_status"] == "no_capture_found" for r in rows),
            "provider_errors": sum(r["wayback_status"] == "provider_error" for r in rows),
        },
    }
    report = merge_report(existing_report, rows, metadata=metadata)
    report["summary"]["cumulative_sources"] = len(report["sources"])
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--shard-count", type=int, default=1)
    parser.add_argument("--delay", type=float, default=0.25)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--backoff", type=float, default=1.0)
    args = parser.parse_args()
    existing = load_json(args.output) if args.output.exists() else None
    report = triangulate(load_json(args.matrix), limit=max(0, args.limit), offset=max(0, args.offset),
                         shard_index=args.shard_index, shard_count=args.shard_count,
                         delay=max(0, args.delay), retries=max(1, args.retries),
                         backoff=max(0, args.backoff), existing_report=existing)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
