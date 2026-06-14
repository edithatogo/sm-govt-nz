import argparse
import datetime as dt
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Protocol

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.archive_bluesky_history import fetch_author_history
from src.archive_schema import NormalizedArchiveRecord, build_normalized_record
from src.archive_state import save_archive_cursor
from src.bluesky import BlueskyPost
from src.feed_ingestion import normalize_feed_entry


class FeedParserModule(Protocol):
    def parse(self, url: str) -> Any:
        """Parse a feed URL into a feedparser-compatible object."""


BlueskyFetcher = Callable[[str], list[dict[str, Any]]]


def archive_current_sources(
    *,
    feed_config_path: str | Path = "config/courts_nz_rss_feeds.json",
    archive_state_path: str | Path = "conductor/archive_state.json",
    health_report_path: str | Path = "conductor/archive_source_health.json",
    raw_root: str | Path = "historical_archive_raw",
    normalized_root: str | Path = "historical_archive_normalized",
    bluesky_actor: str = "did:plc:vtoa673xlou45zcsj6inyeis",
    bluesky_handle: str = "courtsofnz.bsky.social",
    rss_limit_per_feed: int = 20,
    include_bluesky: bool = True,
    include_rss: bool = True,
    bluesky_fetcher: BlueskyFetcher | None = None,
    parser: FeedParserModule | None = None,
) -> dict[str, Any]:
    captured_at = _utc_now()
    health: list[dict[str, Any]] = []
    archived_counts: dict[str, int] = {}

    if include_bluesky:
        try:
            posts = (
                bluesky_fetcher(bluesky_actor)
                if bluesky_fetcher
                else fetch_author_history(bluesky_actor, handle=bluesky_handle, max_pages=1)
            )
            records = [
                _archive_bluesky_post(
                    post,
                    raw_root=Path(raw_root) / "bluesky",
                    captured_at=captured_at,
                )
                for post in posts
            ]
            archived_counts["bluesky"] = _upsert_normalized_records(
                records,
                Path(normalized_root) / "bluesky",
            )
            if posts:
                save_archive_cursor(
                    "courts-nz-bluesky",
                    str(posts[0].get("post_id", "")),
                    archive_state_path,
                )
            health.append(
                _health_entry("courts-nz-bluesky", "healthy", len(posts), archived_counts["bluesky"])
            )
        except Exception as error:
            health.append(_health_entry("courts-nz-bluesky", "unavailable", 0, 0, str(error)))

    if include_rss:
        try:
            rss_records, feed_reports = _archive_current_rss(
                feed_config_path=feed_config_path,
                raw_root=Path(raw_root) / "rss",
                captured_at=captured_at,
                limit_per_feed=rss_limit_per_feed,
                parser=parser,
            )
            archived_counts["rss"] = _upsert_normalized_records(
                rss_records,
                Path(normalized_root) / "rss",
            )
            save_archive_cursor("courts-nz-rss-website", captured_at, archive_state_path)
            health.extend(feed_reports)
        except Exception as error:
            health.append(_health_entry("courts-nz-rss-website", "unavailable", 0, 0, str(error)))

    report = {
        "generated_at": captured_at,
        "archive_only": True,
        "archived_counts": archived_counts,
        "sources": health,
    }
    _write_json_if_changed(Path(health_report_path), report)
    return report


def _archive_bluesky_post(
    post: dict[str, Any],
    *,
    raw_root: Path,
    captured_at: str,
) -> NormalizedArchiveRecord:
    post_id = str(post.get("post_id", ""))
    created_at = str(post.get("created_at", ""))
    month = _month_from_datetime(created_at)
    raw_path = raw_root / month / f"{_safe_id(post_id)}.json"
    raw_payload = {"captured_at": captured_at, "post": post}
    existing_captured_at = _existing_captured_at(raw_path)
    if not raw_path.exists():
        _write_json_if_changed(raw_path, raw_payload)
    return build_normalized_record(
        record_id=f"bluesky:{post_id}",
        agency_id="courts-nz",
        source_platform="bluesky",
        source_account=str(post.get("handle") or "courtsofnz.bsky.social"),
        source_kind="social_feed",
        source_url=str(post.get("url", "")),
        canonical_url=str(post.get("url", "")),
        original_created_at=created_at,
        captured_at=existing_captured_at or captured_at,
        content=str(post.get("text", "")),
        raw_path=str(raw_path).replace("\\", "/"),
        extraction_method="public_at_protocol",
        media_refs=[
            {
                "url": str(image.get("fullsize", "")),
                "media_type": "image",
                "alt_text": str(image.get("alt", "")),
            }
            for image in post.get("images", [])
            if isinstance(image, dict) and image.get("fullsize")
        ],
        cross_source_ids={
            "at_uri": str(post.get("uri", "")),
            "cid": str(post.get("cid", "")),
            "post_id": post_id,
        },
    )


def _archive_current_rss(
    *,
    feed_config_path: str | Path,
    raw_root: Path,
    captured_at: str,
    limit_per_feed: int,
    parser: FeedParserModule | None,
) -> tuple[list[NormalizedArchiveRecord], list[dict[str, Any]]]:
    feed_parser = parser or _load_feedparser()
    feeds = json.loads(Path(feed_config_path).read_text(encoding="utf-8")).get("feeds", [])
    records: list[NormalizedArchiveRecord] = []
    reports: list[dict[str, Any]] = []
    for feed in feeds:
        feed_url = str(feed["feed_url"])
        source_id = "courtsofnz.govt.nz"
        try:
            parsed = feed_parser.parse(feed_url)
            entries = list(getattr(parsed, "entries", []))[:limit_per_feed]
            feed_records = [
                _archive_rss_entry(
                    entry,
                    feed_url=feed_url,
                    source_id=source_id,
                    raw_root=raw_root,
                    captured_at=captured_at,
                )
                for entry in entries
            ]
            records.extend(feed_records)
            reports.append(_health_entry(feed_url, "healthy", len(entries), len(feed_records)))
        except Exception as error:
            reports.append(_health_entry(feed_url, "unavailable", 0, 0, str(error)))
    return records, reports


def _archive_rss_entry(
    entry: Any,
    *,
    feed_url: str,
    source_id: str,
    raw_root: Path,
    captured_at: str,
) -> NormalizedArchiveRecord:
    post: BlueskyPost = normalize_feed_entry(entry, source_id=source_id, feed_url=feed_url)
    month = _month_from_datetime(post["created_at"])
    record_id = _rss_record_id(feed_url, post["url"], post["text"])
    raw_path = raw_root / month / f"{record_id}.json"
    existing_captured_at = _existing_captured_at(raw_path)
    if not raw_path.exists():
        _write_json_if_changed(
            raw_path,
            {
                "captured_at": captured_at,
                "feed_url": feed_url,
                "entry": _json_safe(entry),
            },
        )
    return build_normalized_record(
        record_id=f"rss:{record_id}",
        agency_id="courts-nz",
        source_platform="rss",
        source_account=source_id,
        source_kind="rss_entry",
        source_url=feed_url,
        canonical_url=post["url"],
        original_created_at=post["created_at"],
        captured_at=existing_captured_at or captured_at,
        content=post["text"],
        raw_path=str(raw_path).replace("\\", "/"),
        extraction_method="feedparser",
        cross_source_ids={"feed_url": feed_url, "feed_entry_id": post["post_id"]},
    )


def _upsert_normalized_records(records: list[NormalizedArchiveRecord], normalized_root: Path) -> int:
    by_month: dict[str, list[NormalizedArchiveRecord]] = defaultdict(list)
    for record in records:
        by_month[_month_from_datetime(record["original_created_at"])].append(record)

    for month, month_records in by_month.items():
        shard_path = normalized_root / f"{month}.jsonl"
        existing, existing_order = _load_normalized_shard(shard_path)
        for record in month_records:
            previous = existing.get(record["record_id"])
            if previous and previous.get("content_hash") == record["content_hash"]:
                record["captured_at"] = str(previous.get("captured_at", record["captured_at"]))
            if record["record_id"] not in existing:
                existing_order.append(record["record_id"])
            existing[record["record_id"]] = record
        _write_jsonl_if_changed(shard_path, existing, existing_order)
    return len(records)


def _load_normalized_shard(path: Path) -> tuple[dict[str, NormalizedArchiveRecord], list[str]]:
    if not path.exists():
        return {}, []
    records: dict[str, NormalizedArchiveRecord] = {}
    order: list[str] = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            record = json.loads(line)
            record_id = str(record["record_id"])
            records[record_id] = record
            order.append(record_id)
    return records, order


def _write_jsonl_if_changed(
    path: Path,
    records: dict[str, NormalizedArchiveRecord],
    record_order: list[str],
) -> None:
    lines = [json.dumps(records[record_id], ensure_ascii=False, sort_keys=True) for record_id in record_order]
    content = "\n".join(lines) + ("\n" if lines else "")
    _write_text_if_changed(path, content)


def _write_json_if_changed(path: Path, payload: Any) -> None:
    _write_text_if_changed(
        path,
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
    )


def _write_text_if_changed(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return
    path.write_text(content, encoding="utf-8")


def _health_entry(
    source_id: str,
    status: str,
    observed_count: int,
    archived_count: int,
    error: str = "",
) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "status": status,
        "observed_count": observed_count,
        "archived_count": archived_count,
        "error": error,
    }


def _existing_captured_at(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ""
    return str(payload.get("captured_at", ""))


def _rss_record_id(feed_url: str, entry_url: str, text: str) -> str:
    value = f"{feed_url}\n{entry_url}\n{text}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def _month_from_datetime(value: str) -> str:
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.date().strftime("%Y-%m")
    except ValueError:
        return dt.datetime.now(dt.timezone.utc).date().strftime("%Y-%m")


def _safe_id(value: str) -> str:
    safe = "".join(char for char in value if char.isalnum() or char in ("-", "_", ".")).strip()
    return safe or "unknown"


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _load_feedparser() -> FeedParserModule:
    try:
        import feedparser
    except ImportError as error:
        raise RuntimeError("Install feedparser to archive RSS feeds.") from error
    return feedparser


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def main() -> None:
    parser = argparse.ArgumentParser(description="Archive current Courts NZ public source records.")
    parser.add_argument("--feed-config", default="config/courts_nz_rss_feeds.json")
    parser.add_argument("--archive-state", default="conductor/archive_state.json")
    parser.add_argument("--health-report", default="conductor/archive_source_health.json")
    parser.add_argument("--raw-root", default="historical_archive_raw")
    parser.add_argument("--normalized-root", default="historical_archive_normalized")
    parser.add_argument("--rss-limit-per-feed", type=int, default=20)
    parser.add_argument("--skip-bluesky", action="store_true")
    parser.add_argument("--skip-rss", action="store_true")
    args = parser.parse_args()

    report = archive_current_sources(
        feed_config_path=args.feed_config,
        archive_state_path=args.archive_state,
        health_report_path=args.health_report,
        raw_root=args.raw_root,
        normalized_root=args.normalized_root,
        rss_limit_per_feed=args.rss_limit_per_feed,
        include_bluesky=not args.skip_bluesky,
        include_rss=not args.skip_rss,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
