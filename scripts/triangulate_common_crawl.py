"""Collect Common Crawl index metadata without downloading crawl payloads."""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.error import HTTPError
from urllib.request import Request, urlopen

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


def triangulate(matrix: dict, *, limit: int = 100, delay: float = 0.25) -> dict:
    rows: list[dict] = []
    try:
        index_url = latest_index()
        index_status = "index_available"
    except Exception as exc:
        index_url = ""
        index_status = "provider_error"
        index_error = f"{type(exc).__name__}: {exc}"
    for source in (matrix.get("sources") or [])[: max(0, limit)]:
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
                captures = query_index(index_url, url)
                result["captures"] = captures
                result["capture_count"] = len(captures)
                result["common_crawl_status"] = "capture_metadata_found" if captures else "no_capture_found"
            except Exception as exc:
                if getattr(exc, "code", None) == 404:
                    result["common_crawl_status"] = "no_capture_found"
                else:
                    result["common_crawl_status"] = "provider_error"
                    result["error"] = f"{type(exc).__name__}: {exc}"
        rows.append(result)
        if delay:
            time.sleep(delay)
    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "provider": "common_crawl_index",
        "purpose": "independent historical corroboration metadata; not canonical capture",
        "snapshot_downloaded": False,
        "index_url": index_url,
        "source_limit": limit,
        "summary": {
            "sources_checked": len(rows),
            "capture_metadata_sources": sum(r["common_crawl_status"] == "capture_metadata_found" for r in rows),
            "no_capture_sources": sum(r["common_crawl_status"] == "no_capture_found" for r in rows),
            "provider_errors": sum(r["common_crawl_status"] == "provider_error" for r in rows),
        },
        "sources": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--delay", type=float, default=0.25)
    args = parser.parse_args()
    report = triangulate(json.loads(args.matrix.read_text(encoding="utf-8")), limit=args.limit, delay=args.delay)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
