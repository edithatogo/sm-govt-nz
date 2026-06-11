import hashlib
import html
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Protocol

from src.bluesky import BlueskyPost


class FeedParserModule(Protocol):
    def parse(self, url: str) -> Any:
        """Parse a feed URL into a feedparser-compatible object."""


def fetch_feed_posts(
    feed_url: str,
    *,
    source_id: str,
    parser: FeedParserModule | None = None,
    limit: int = 20,
) -> list[BlueskyPost]:
    """Fetch RSS/Atom entries and normalize them to the project post contract."""
    feed_parser = parser or _load_feedparser()
    feed = feed_parser.parse(feed_url)
    posts = [
        normalize_feed_entry(entry, source_id=source_id, feed_url=feed_url)
        for entry in list(getattr(feed, "entries", []))[:limit]
    ]
    return list(reversed(posts))


def normalize_feed_entry(entry: Any, *, source_id: str, feed_url: str) -> BlueskyPost:
    link = str(_entry_value(entry, "link", ""))
    title = _clean_text(str(_entry_value(entry, "title", "")))
    summary = _clean_text(str(_entry_value(entry, "summary", "")))
    text = title if not summary else f"{title}\n\n{summary}"
    created_at = _entry_datetime(entry)
    post_id = _stable_id(source_id, link or text or created_at)

    return {
        "post_id": post_id,
        "uri": link or f"feed:{feed_url}#{post_id}",
        "cid": post_id,
        "handle": source_id,
        "author_did": "",
        "text": text,
        "created_at": created_at,
        "url": link or feed_url,
        "images": [],
    }


def _load_feedparser() -> FeedParserModule:
    try:
        import feedparser
    except ImportError as error:
        raise RuntimeError("Install feedparser to ingest RSS/Atom feeds.") from error
    return feedparser


def _entry_value(entry: Any, key: str, default: Any) -> Any:
    if isinstance(entry, dict):
        return entry.get(key, default)
    return getattr(entry, key, default)


def _entry_datetime(entry: Any) -> str:
    raw_value = _entry_value(entry, "published", "") or _entry_value(entry, "updated", "")
    if raw_value:
        try:
            parsed = parsedate_to_datetime(str(raw_value))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc).isoformat()
        except (TypeError, ValueError):
            return str(raw_value)
    return datetime.now(timezone.utc).isoformat()


def _clean_text(value: str) -> str:
    return html.unescape(value).replace("\r", "").strip()


def _stable_id(source_id: str, value: str) -> str:
    return hashlib.sha256(f"{source_id}:{value}".encode("utf-8")).hexdigest()[:24]
