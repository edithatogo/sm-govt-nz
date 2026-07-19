"""Collect Common Crawl index metadata without downloading crawl payloads."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.error import HTTPError
from urllib.request import Request, URLError, urlopen

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MATRIX = ROOT / "conductor/archive_completion_matrix.json"
DEFAULT_OUTPUT = ROOT / "conductor/archive_triangulation_common_crawl.json"
COLLECTIONS_URL = "https://index.commoncrawl.org/collinfo.json"


def fetch_json(url: str, *, timeout: int = 30, opener=urlopen):
    request = Request(url, headers={"User-Agent": "sm-govt-nz/common-crawl-triangulation"})
    with opener(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def latest_index(*, timeout: int = 30, opener=urlopen) -> str:
    collections = fetch_json(COLLECTIONS_URL, timeout=timeout, opener=opener)
    if not collections:
        raise RuntimeError("Common Crawl returned no collections")
    return str(collections[0]["cdx-api"])


def query_index(index_url: str, url: str, *, timeout: int = 30, opener=urlopen) -> list[dict]:
    params = {
        "url": url,
        "output": "json",
        "filter": ["status:200", "mime:text/html"],
        "collapse": "digest",
        "limit": "20",
    }
    request = Request(
        f"{index_url}?{urlencode(params, doseq=True)}",
        headers={"User-Agent": "sm-govt-nz/common-crawl-triangulation"},
    )
    try:
        with opener(request, timeout=timeout) as response:
            rows = []
            for line in response.read().decode("utf-8").splitlines():
                if line.strip():
                    rows.append(json.loads(line))
            return rows
    except HTTPError as exc:
        if exc.code == 404:
            return []
        raise


def is_transient(exc: Exception) -> bool:
    code = getattr(exc, "code", None)
    return isinstance(exc, (TimeoutError, URLError)) or code in {408, 425, 429, 500, 502, 503, 504}


def with_retries(operation, *, retries: int = 3, backoff: float = 1.0, max_backoff: float = 30.0):
    for attempt in range(max(1, retries)):
        try:
            return operation()
        except Exception as exc:
            if attempt + 1 >= max(1, retries) or not is_transient(exc):
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
    return {**metadata, "sources": list(prior.values())}


def triangulate(matrix: dict, *, limit: int = 100, offset: int = 0, shard_index: int = 0,
               shard_count: int = 1, delay: float = 0.25, retries: int = 3,
               backoff: float = 1.0, existing_report: dict | None = None) -> dict:
    if shard_count < 1 or not 0 <= shard_index < shard_count:
        raise ValueError("shard_index must be within shard_count")
    rows: list[dict] = []
    try:
        index_url = with_retries(lambda: latest_index(), retries=retries, backoff=backoff)
        index_status = "index_available"
    except Exception as exc:
        index_url = ""
        index_status = "provider_error"
        index_error = f"{type(exc).__name__}: {exc}"
    selected_sources = select_sources(matrix.get("sources") or [], limit=max(0, limit), offset=max(0, offset),
                                      shard_index=shard_index, shard_count=shard_count)
    for source in selected_sources:
        url = str(source.get("url") or "")
        result = {
            "source_id": source.get("source_id"),
            "platform": source.get("platform"),
            "url": url,
            "common_crawl_status": "not_checked",
            "capture_count": 0,
            "captures": [],
        }
        if index_status != "index_available":
            result["common_crawl_status"] = index_status
            result["error"] = index_error
        elif not url.startswith(("http://", "https://")):
            result["common_crawl_status"] = "unsupported_url"
        else:
            try:
                captures = with_retries(lambda: query_index(index_url, url), retries=retries, backoff=backoff)
                result["captures"] = captures
                result["capture_count"] = len(captures)
                result["common_crawl_status"] = "capture_metadata_found" if captures else "no_capture_found"
            except Exception as exc:
                if getattr(exc, "code", None) == 404 or "HTTP Error 404" in str(exc):
                    result["common_crawl_status"] = "no_capture_found"
                else:
                    result["common_crawl_status"] = "provider_error"
                    result["error"] = f"{type(exc).__name__}: {exc}"
        rows.append(result)
        if delay:
            time.sleep(delay)
    metadata = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "matrix_revision": os.environ.get("GITHUB_SHA"),
        "provider": "common_crawl_index",
        "purpose": "independent historical corroboration metadata; not canonical capture",
        "snapshot_downloaded": False,
        "index_url": index_url,
        "source_limit": limit,
        "batch": {"offset": max(0, offset), "shard_index": shard_index, "shard_count": shard_count,
                  "selected_sources": len(rows)},
        "summary": {
            "sources_checked": len(rows),
            "capture_metadata_sources": sum(r["common_crawl_status"] == "capture_metadata_found" for r in rows),
            "no_capture_sources": sum(r["common_crawl_status"] == "no_capture_found" for r in rows),
            "provider_errors": sum(r["common_crawl_status"] == "provider_error" for r in rows),
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
    existing = json.loads(args.output.read_text(encoding="utf-8")) if args.output.exists() else None
    report = triangulate(json.loads(args.matrix.read_text(encoding="utf-8")), limit=max(0, args.limit),
                         offset=max(0, args.offset), shard_index=args.shard_index, shard_count=args.shard_count,
                         delay=max(0, args.delay), retries=max(1, args.retries), backoff=max(0, args.backoff),
                         existing_report=existing)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
