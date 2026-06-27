import argparse
import datetime as dt
import hashlib
import json
import sys
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable, Protocol
from urllib.parse import urlparse
from urllib.request import Request, urlopen

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
WebsiteFetcher = Callable[[str], str]


def archive_current_sources(
    *,
    feed_config_path: str | Path = "config/courts-of-nz_rss_feeds.json",
    archive_state_path: str | Path = "conductor/archive_state.json",
    health_report_path: str | Path = "conductor/archive_source_health.json",
    raw_root: str | Path = "historical_archive_raw",
    normalized_root: str | Path = "historical_archive_normalized",
    bluesky_actor: str = "did:plc:vtoa673xlou45zcsj6inyeis",
    bluesky_handle: str = "courtsofnz.bsky.social",
    rss_limit_per_feed: int = 20,
    website_limit: int = 20,
    include_bluesky: bool = True,
    include_rss: bool = True,
    include_website: bool = True,
    bluesky_fetcher: BlueskyFetcher | None = None,
    website_fetcher: WebsiteFetcher | None = None,
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
            save_archive_cursor("courts-nz-rss-website", _records_cursor(rss_records), archive_state_path)
            health.extend(feed_reports)
            if include_website:
                website_records, website_report = _archive_linked_website_pages(
                    source_records=rss_records,
                    raw_root=Path(raw_root) / "website",
                    captured_at=captured_at,
                    limit=website_limit,
                    fetcher=website_fetcher,
                )
                archived_counts["website"] = _upsert_normalized_records(
                    website_records,
                    Path(normalized_root) / "website",
                )
                save_archive_cursor(
                    "courts-nz-website-pages",
                    _records_cursor(website_records),
                    archive_state_path,
                )
                health.append(website_report)
        except Exception as error:
            health.append(_health_entry("courts-nz-rss-website", "unavailable", 0, 0, str(error)))

    report = {
        "generated_at": captured_at,
        "archive_only": True,
        "archived_counts": archived_counts,
        "sources": health,
    }
    _write_health_report_if_changed(Path(health_report_path), report)
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


def _archive_linked_website_pages(
    *,
    source_records: list[NormalizedArchiveRecord],
    raw_root: Path,
    captured_at: str,
    limit: int,
    fetcher: WebsiteFetcher | None,
) -> tuple[list[NormalizedArchiveRecord], dict[str, Any]]:
    urls = _website_urls_from_records(source_records)[:limit]
    records: list[NormalizedArchiveRecord] = []
    failures: list[str] = []
    for url in urls:
        try:
            source_record = next(record for record in source_records if record["canonical_url"] == url)
            html = _existing_website_raw_html(
                url=url,
                source_record=source_record,
                raw_root=raw_root,
            )
            if not html:
                html = fetcher(url) if fetcher else _fetch_website_html(url)
            records.append(
                _archive_website_page(
                    url=url,
                    html=html,
                    source_record=source_record,
                    raw_root=raw_root,
                    captured_at=captured_at,
                )
            )
        except Exception as error:
            failures.append(f"{url}: {error}")
    status = "healthy" if not failures else "degraded"
    return records, _health_entry(
        "courts-nz-website-pages",
        status,
        len(urls),
        len(records),
        "; ".join(failures[:3]),
    )


def _existing_website_raw_html(
    *,
    url: str,
    source_record: NormalizedArchiveRecord,
    raw_root: Path,
) -> str:
    month = _month_from_datetime(source_record["original_created_at"])
    raw_path = raw_root / month / f"{_website_record_id(url)}.json"
    if not raw_path.exists():
        return ""
    try:
        payload = json.loads(raw_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ""
    return str(payload.get("html", ""))


def _archive_website_page(
    *,
    url: str,
    html: str,
    source_record: NormalizedArchiveRecord,
    raw_root: Path,
    captured_at: str,
) -> NormalizedArchiveRecord:
    parsed = _ParsedHtml.from_html(html)
    month = _month_from_datetime(source_record["original_created_at"])
    record_id = _website_record_id(url)
    raw_path = raw_root / month / f"{record_id}.json"
    existing_captured_at = _existing_captured_at(raw_path)
    if not raw_path.exists():
        _write_json_if_changed(
            raw_path,
            {
                "captured_at": captured_at,
                "url": url,
                "html": html,
                "source_record_id": source_record["record_id"],
            },
        )
    return build_normalized_record(
        record_id=f"website:{record_id}",
        agency_id="courts-nz",
        source_platform="courtsofnz.govt.nz",
        source_account="courtsofnz.govt.nz",
        source_kind="website_page",
        source_url=url,
        canonical_url=url,
        original_created_at=source_record["original_created_at"],
        captured_at=existing_captured_at or captured_at,
        content=parsed.content,
        raw_path=str(raw_path).replace("\\", "/"),
        extraction_method="public_html",
        cross_source_ids={
            "source_record_id": source_record["record_id"],
            "source_content_hash": source_record["content_hash"],
        },
    )


def _website_urls_from_records(records: list[NormalizedArchiveRecord]) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for record in records:
        url = record["canonical_url"]
        if not _is_courts_website_url(url) or url in seen:
            continue
        seen.add(url)
        urls.append(url)
    return urls


def _is_courts_website_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and parsed.netloc.lower() in {
        "www.courtsofnz.govt.nz",
        "courtsofnz.govt.nz",
    }


def _fetch_website_html(url: str) -> str:
    request = Request(url, headers={"User-Agent": "sm-govt-nz-archive/1.0"})
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


class _ParsedHtml(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self._in_title = False
        self.title_parts: list[str] = []
        self.body_parts: list[str] = []

    @classmethod
    def from_html(cls, html: str) -> "_ParsedHtml":
        parser = cls()
        parser.feed(html)
        return parser

    @property
    def content(self) -> str:
        title = " ".join(" ".join(self.title_parts).split())
        body = " ".join(" ".join(self.body_parts).split())
        if title and body and title not in body:
            return f"{title}\n\n{body}"
        return body or title

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_name = tag.lower()
        if tag_name in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
        if tag_name == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        tag_name = tag.lower()
        if tag_name in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
        if tag_name == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        value = data.strip()
        if not value or self._skip_depth:
            return
        if self._in_title:
            self.title_parts.append(value)
        else:
            self.body_parts.append(value)


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


def _write_health_report_if_changed(path: Path, report: dict[str, Any]) -> None:
    stable_report = dict(report)
    if path.exists():
        try:
            previous = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            previous = {}
        previous_stable = dict(previous)
        previous_stable.pop("generated_at", None)
        current_stable = dict(report)
        current_stable.pop("generated_at", None)
        if previous_stable == current_stable:
            return
    _write_json_if_changed(path, stable_report)


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


def _website_record_id(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]


def _records_cursor(records: list[NormalizedArchiveRecord]) -> str:
    if not records:
        return "empty"
    payload = {
        "count": len(records),
        "latest_original_created_at": max(record["original_created_at"] for record in records),
        "record_ids": sorted(record["record_id"] for record in records),
    }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


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
    parser.add_argument("--feed-config", default="config/courts-of-nz_rss_feeds.json")
    parser.add_argument("--archive-state", default="conductor/archive_state.json")
    parser.add_argument("--health-report", default="conductor/archive_source_health.json")
    parser.add_argument("--raw-root", default="historical_archive_raw")
    parser.add_argument("--normalized-root", default="historical_archive_normalized")
    parser.add_argument("--rss-limit-per-feed", type=int, default=20)
    parser.add_argument("--website-limit", type=int, default=20)
    parser.add_argument("--skip-bluesky", action="store_true")
    parser.add_argument("--skip-rss", action="store_true")
    parser.add_argument("--skip-website", action="store_true")
    args = parser.parse_args()

    report = archive_current_sources(
        feed_config_path=args.feed_config,
        archive_state_path=args.archive_state,
        health_report_path=args.health_report,
        raw_root=args.raw_root,
        normalized_root=args.normalized_root,
        rss_limit_per_feed=args.rss_limit_per_feed,
        website_limit=args.website_limit,
        include_bluesky=not args.skip_bluesky,
        include_rss=not args.skip_rss,
        include_website=not args.skip_website,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
