import datetime as dt
import json
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable
from urllib.parse import urldefrag, urljoin
from urllib.request import Request, urlopen

from src.source_inventory import SourceInventory, load_source_inventory


Fetcher = Callable[[str], str]


RSS_MIME_TYPES = {
    "application/atom+xml",
    "application/feed+json",
    "application/rdf+xml",
    "application/rss+xml",
    "application/xml",
    "text/xml",
}


@dataclass(frozen=True)
class DiscoveredFeed:
    feed_url: str
    seed_page: str
    title: str
    feed_type: str
    discovery_method: str


@dataclass(frozen=True)
class SeedPageResult:
    seed_page: str
    status: str
    feed_count: int
    error: str = ""


@dataclass(frozen=True)
class RssDiscoveryReport:
    generated_at: str
    agency_id: str
    seed_page_count: int
    feed_count: int
    feeds: list[DiscoveredFeed]
    seed_pages: list[SeedPageResult]


class FeedLinkParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url
        self.feeds: list[DiscoveredFeed] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key.lower(): value or "" for key, value in attrs}
        href = attr_map.get("href", "").strip()
        if not href:
            return

        if tag.lower() == "link" and _is_feed_link(attr_map):
            self._add_feed(
                href=href,
                title=attr_map.get("title", ""),
                feed_type=attr_map.get("type", ""),
                discovery_method="link-rel-alternate",
            )
        elif tag.lower() == "a" and _looks_like_feed_href(href, attr_map.get("title", "")):
            self._add_feed(
                href=href,
                title=attr_map.get("title", ""),
                feed_type=attr_map.get("type", ""),
                discovery_method="anchor-feed-link",
            )

    def _add_feed(
        self,
        *,
        href: str,
        title: str,
        feed_type: str,
        discovery_method: str,
    ) -> None:
        absolute_url = _normalize_url(urljoin(self.base_url, href))
        self.feeds.append(
            DiscoveredFeed(
                feed_url=absolute_url,
                seed_page=self.base_url,
                title=title.strip(),
                feed_type=feed_type.strip(),
                discovery_method=discovery_method,
            )
        )


def discover_courts_rss_feeds(
    inventory: SourceInventory | None = None,
    *,
    fetcher: Fetcher | None = None,
    generated_at: str | None = None,
) -> RssDiscoveryReport:
    source_inventory = inventory or load_source_inventory()
    contract = next(
        (
            item
            for item in source_inventory["contracts"]
            if item.get("id") == "courts-nz-rss-website"
        ),
        None,
    )
    if contract is None:
        raise ValueError("Missing courts-nz-rss-website source contract.")

    seed_pages = [str(page) for page in contract.get("seed_pages", [])]
    return discover_rss_feeds(
        agency_id=source_inventory["agency_id"],
        seed_pages=seed_pages,
        fetcher=fetcher,
        generated_at=generated_at,
    )


def discover_rss_feeds(
    *,
    agency_id: str,
    seed_pages: list[str],
    fetcher: Fetcher | None = None,
    generated_at: str | None = None,
) -> RssDiscoveryReport:
    page_fetcher = fetcher or fetch_url
    feeds_by_url: dict[str, DiscoveredFeed] = {}
    page_results: list[SeedPageResult] = []

    for seed_page in seed_pages:
        try:
            html = page_fetcher(seed_page)
            parser = FeedLinkParser(seed_page)
            parser.feed(html)
            for feed in parser.feeds:
                feeds_by_url.setdefault(feed.feed_url, feed)
            page_results.append(
                SeedPageResult(
                    seed_page=seed_page,
                    status="healthy",
                    feed_count=len(parser.feeds),
                )
            )
        except Exception as error:
            page_results.append(
                SeedPageResult(
                    seed_page=seed_page,
                    status="unavailable",
                    feed_count=0,
                    error=str(error),
                )
            )

    feeds = sorted(feeds_by_url.values(), key=lambda feed: feed.feed_url)
    return RssDiscoveryReport(
        generated_at=generated_at or dt.datetime.now(dt.timezone.utc).isoformat(),
        agency_id=agency_id,
        seed_page_count=len(seed_pages),
        feed_count=len(feeds),
        feeds=feeds,
        seed_pages=page_results,
    )


def write_rss_discovery_report(
    report: RssDiscoveryReport,
    path: str | Path = "config/courts_nz_rss_feeds.json",
) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(asdict(report), indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def fetch_url(url: str) -> str:
    request = Request(
        url,
        headers={"User-Agent": "sm-govt-nz-rss-discovery/1.0"},
    )
    with urlopen(request, timeout=30) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def _is_feed_link(attrs: dict[str, str]) -> bool:
    rel_values = {value.strip().lower() for value in attrs.get("rel", "").split()}
    mime_type = attrs.get("type", "").lower()
    return "alternate" in rel_values and mime_type in RSS_MIME_TYPES


def _looks_like_feed_href(href: str, title: str) -> bool:
    value = f"{href} {title}".lower()
    return any(marker in value for marker in ("rss", "atom", "feed.xml", "feed/"))


def _normalize_url(url: str) -> str:
    return urldefrag(url)[0]
