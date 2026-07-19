"""Collect compact Internet Archive CDX evidence for registered sources.

This is corroboration metadata only. It does not download or republish archived
snapshots and never writes to the Internet Archive.
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlencode
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


def triangulate(matrix: dict, *, limit: int = 100, delay: float = 0.25) -> dict:
    sources = matrix.get("sources") or []
    rows: list[dict] = []
    for source in sources[:limit]:
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
                captures = query_wayback(url)
                result["captures"] = captures
                result["capture_count"] = len(captures)
                result["wayback_status"] = "capture_metadata_found" if captures else "no_capture_found"
            except Exception as exc:  # network/provider failures are reportable per source
                result["wayback_status"] = "provider_error"
                result["error"] = f"{type(exc).__name__}: {exc}"
        rows.append(result)
        if delay:
            time.sleep(delay)
    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "provider": "internet_archive_wayback_cdx",
        "purpose": "independent historical corroboration metadata; not canonical capture",
        "snapshot_downloaded": False,
        "source_limit": limit,
        "summary": {
            "sources_checked": len(rows),
            "capture_metadata_sources": sum(r["wayback_status"] == "capture_metadata_found" for r in rows),
            "no_capture_sources": sum(r["wayback_status"] == "no_capture_found" for r in rows),
            "provider_errors": sum(r["wayback_status"] == "provider_error" for r in rows),
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
    report = triangulate(load_json(args.matrix), limit=max(0, args.limit), delay=max(0, args.delay))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
