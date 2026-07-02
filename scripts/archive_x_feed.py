import argparse
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.archive_x_browser import (  # noqa: E402
    append_normalized_record,
    dedupe_x_sources,
    normalize_x_handle,
    now_iso,
    source_result,
    stable_id,
)
from src.archive_schema import build_normalized_record  # noqa: E402


DEFAULT_MANIFEST = Path("conductor/govt_archive_source_manifest.json")
DEFAULT_REPORT = Path("conductor/x_feed_archive_report.json")
DEFAULT_RAW_ROOT = Path("historical_archive_raw")
DEFAULT_NORMALIZED_ROOT = Path("historical_archive_normalized")
DEFAULT_PROVIDERS = ["rsshub", "nitter"]
DEFAULT_RSSHUB_BASE_URLS = ["https://rsshub.app"]
DEFAULT_NITTER_BASE_URLS = [
    "https://xcancel.com",
    "https://nitter.poast.org",
    "https://nitter.privacyredirect.com",
    "https://lightbrd.com",
    "https://nitter.space",
    "https://nitter.tiekoetter.com",
    "https://nuku.trabun.org",
    "https://nitter.catsarch.com",
    "https://nitter.kareem.one",
    "https://nt.vern.cc",
]
SUPPORTED_PROVIDERS = {"rsshub", "nitter", "twscrape", "scweet"}
STATUS_URL_RE = re.compile(r"https?://(?:www\.)?(?:x|twitter)\.com/([^/?#]+)/status/(\d+)")


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def providers_from_value(value: str | list[str] | None) -> list[str]:
    providers = split_csv(value) if isinstance(value, str) else list(value or [])
    normalized = []
    for provider in providers or DEFAULT_PROVIDERS:
        name = provider.strip().lower()
        if name in SUPPORTED_PROVIDERS and name not in normalized:
            normalized.append(name)
    return normalized or list(DEFAULT_PROVIDERS)


def base_urls_from_value(value: str | list[str] | None, defaults: list[str]) -> list[str]:
    urls = split_csv(value) if isinstance(value, str) else list(value or [])
    return [url.rstrip("/") for url in (urls or defaults) if url.strip()]


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name, "").strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}


def build_feed_urls(
    provider: str,
    handle: str,
    *,
    rsshub_base_urls: list[str],
    nitter_base_urls: list[str],
) -> list[str]:
    quoted = quote(handle.lstrip("@"), safe="")
    if provider == "rsshub":
        return [f"{base.rstrip('/')}/twitter/user/{quoted}" for base in rsshub_base_urls]
    if provider == "nitter":
        return [f"{base.rstrip('/')}/{quoted}/rss" for base in nitter_base_urls]
    return []


def fetch_feed_text(url: str, timeout: int = 30) -> str:
    request = Request(
        url,
        headers={
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
            "User-Agent": "sm-govt-nz-x-feed-archive/1.0 (+https://github.com/edithatogo/sm-govt-nz)",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def feed_error_status(error: Exception) -> str:
    if isinstance(error, HTTPError):
        if error.code in {401, 403}:
            return "feed_blocked"
        if error.code == 404:
            return "feed_not_found"
        if error.code == 429:
            return "feed_rate_limited"
        if 500 <= error.code < 600:
            return "provider_unavailable"
    if isinstance(error, URLError):
        return "provider_unavailable"
    return "feed_fetch_failed"


def feed_error_reason(error: Exception) -> str:
    if isinstance(error, HTTPError):
        body = error.read().decode("utf-8", errors="replace")
        return f"HTTP {error.code} {body[:300]}".strip()
    return str(error)[:300]


def parse_feed(body: str) -> Any:
    import feedparser

    return feedparser.parse(body)


def entry_value(entry: Any, key: str, default: str = "") -> str:
    value = entry.get(key, default) if hasattr(entry, "get") else default
    return str(value or default)


def entry_created_at(entry: Any, fallback: str) -> str:
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        value = entry.get(key) if hasattr(entry, "get") else None
        if value:
            return datetime(*value[:6], tzinfo=timezone.utc).replace(microsecond=0).isoformat()
    for key in ("published", "updated", "created"):
        value = entry_value(entry, key)
        if not value:
            continue
        try:
            parsed = parsedate_to_datetime(value)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat()
        except (TypeError, ValueError):
            continue
    return fallback


def entry_content(entry: Any) -> str:
    parts = [entry_value(entry, "title")]
    summary = entry_value(entry, "summary") or entry_value(entry, "description")
    if summary and summary not in parts:
        parts.append(summary)
    content_items = entry.get("content", []) if hasattr(entry, "get") else []
    if isinstance(content_items, list):
        for item in content_items:
            if isinstance(item, dict):
                value = str(item.get("value") or "")
                if value and value not in parts:
                    parts.append(value)
    return "\n\n".join(part for part in parts if part).strip()


def canonical_x_url(entry: Any, handle: str) -> tuple[str, str]:
    candidates = [
        entry_value(entry, "link"),
        entry_value(entry, "id"),
        entry_value(entry, "guid"),
        entry_content(entry),
    ]
    for candidate in candidates:
        match = STATUS_URL_RE.search(candidate)
        if match:
            tweet_id = match.group(2)
            return f"https://x.com/{match.group(1)}/status/{tweet_id}", tweet_id
    link = entry_value(entry, "link")
    if link:
        return link.replace("https://twitter.com/", "https://x.com/"), ""
    return f"https://x.com/{handle}", ""


def write_raw_feed(
    *,
    raw_root: Path,
    provider: str,
    source: dict[str, Any],
    handle: str,
    feed_url: str,
    body: str,
    captured_at: str,
    parsed_entry_count: int,
) -> Path:
    key = stable_id(f"{provider}|{source.get('source_id')}|{handle}|{feed_url}|{captured_at[:10]}")
    raw_path = raw_root / "x_feed" / captured_at[:7] / f"{provider}_{handle.lower()}_{key}.json"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(
        json.dumps(
            {
                "captured_at": captured_at,
                "provider": provider,
                "source": source,
                "handle": handle,
                "feed_url": feed_url,
                "body": body,
                "parsed_entry_count": parsed_entry_count,
                "policy": {
                    "access_method": f"{provider}_public_feed",
                    "no_login": True,
                    "no_proxy": True,
                    "no_captcha_solving": True,
                    "no_private_graphql": True,
                    "not_full_historical_export": True,
                },
            },
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return raw_path


def normalize_feed_entries(
    *,
    provider: str,
    source: dict[str, Any],
    handle: str,
    entries: list[Any],
    raw_path: Path,
    normalized_root: Path,
    captured_at: str,
    max_items: int,
) -> tuple[int, int]:
    captured = 0
    already = 0
    for entry in entries[:max_items]:
        canonical_url, tweet_id = canonical_x_url(entry, handle)
        content = entry_content(entry)
        created_at = entry_created_at(entry, captured_at)
        fingerprint = stable_id(
            "|".join(
                [
                    provider,
                    handle.lower(),
                    tweet_id,
                    canonical_url,
                    entry_value(entry, "id"),
                    entry_value(entry, "title"),
                    created_at,
                ]
            )
        )
        record_key = tweet_id or fingerprint
        record = build_normalized_record(
            record_id=f"x_feed:{record_key}",
            agency_id=str(source.get("agency_id") or ""),
            source_platform="x",
            source_account=handle,
            source_kind="public_feed_post",
            source_url=str(source.get("url") or f"https://x.com/{handle}"),
            canonical_url=canonical_url,
            original_created_at=created_at,
            captured_at=captured_at,
            content=content or "X public feed entry captured; feed did not expose text content.",
            raw_path=str(raw_path).replace("\\", "/"),
            extraction_method=f"x_{provider}_feed",
            cross_source_ids={
                "source_id": str(source.get("source_id") or ""),
                "duplicate_source_ids": ",".join(source.get("duplicate_source_ids", [])),
                "x_username": handle,
                "x_post_id": tweet_id,
                "feed_entry_id": entry_value(entry, "id") or entry_value(entry, "guid"),
                "feed_provider": provider,
            },
        )
        if append_normalized_record(normalized_root, "x", record):
            captured += 1
        else:
            already += 1
    return captured, already


def archive_feed_provider(
    source: dict[str, Any],
    provider: str,
    *,
    handle: str,
    raw_root: Path,
    normalized_root: Path,
    feed_urls: list[str],
    timeout: int,
    max_items: int,
    fetcher: Any | None = None,
) -> dict[str, Any]:
    attempts: list[dict[str, str]] = []
    fetch = fetcher or fetch_feed_text
    last_empty: dict[str, Any] | None = None
    for feed_url in feed_urls:
        captured_at = now_iso()
        try:
            body = fetch(feed_url, timeout=timeout)
            parsed = parse_feed(body)
        except Exception as exc:  # noqa: BLE001 - provider failures are report states.
            attempts.append({"feed_url": feed_url, "status": feed_error_status(exc), "reason": feed_error_reason(exc)})
            continue
        entries = list(getattr(parsed, "entries", []) or [])
        raw_path = write_raw_feed(
            raw_root=raw_root,
            provider=provider,
            source=source,
            handle=handle,
            feed_url=feed_url,
            body=body,
            captured_at=captured_at,
            parsed_entry_count=len(entries),
        )
        if not entries:
            last_empty = {
                "feed_url": feed_url,
                "status": "feed_empty",
                "reason": "provider returned a parseable feed with no entries",
                "raw_path": str(raw_path).replace("\\", "/"),
            }
            attempts.append({"feed_url": feed_url, "status": "feed_empty", "reason": "no entries"})
            continue
        captured_count, already_count = normalize_feed_entries(
            provider=provider,
            source=source,
            handle=handle,
            entries=entries,
            raw_path=raw_path,
            normalized_root=normalized_root,
            captured_at=captured_at,
            max_items=max_items,
        )
        status = "feed_captured" if captured_count else "feed_already_captured"
        return source_result(
            source,
            status,
            f"{provider} feed entries={len(entries)} captured={captured_count} already={already_count}",
            provider=provider,
            handle=handle,
            feed_url=feed_url,
            raw_path=str(raw_path).replace("\\", "/"),
            attempts=attempts,
        )
    if last_empty:
        return source_result(
            source,
            "feed_empty",
            last_empty["reason"],
            provider=provider,
            handle=handle,
            feed_url=last_empty["feed_url"],
            raw_path=last_empty["raw_path"],
            attempts=attempts,
        )
    status_counts = Counter(attempt["status"] for attempt in attempts)
    status = status_counts.most_common(1)[0][0] if status_counts else "provider_unconfigured"
    reason = "; ".join(f"{item['feed_url']}: {item['status']} {item['reason']}" for item in attempts[:3])
    return source_result(
        source,
        status,
        reason or f"{provider} has no configured feed URLs",
        provider=provider,
        handle=handle,
        feed_url=attempts[0]["feed_url"] if attempts else "",
        attempts=attempts,
    )


def archive_auth_scrape_stub(
    source: dict[str, Any],
    provider: str,
    *,
    handle: str,
    enable_auth_scrape: bool,
) -> dict[str, Any]:
    if not enable_auth_scrape:
        return source_result(
            source,
            "auth_scrape_disabled",
            f"{provider} requires operator-authorized X account cookies and is disabled by default",
            provider=provider,
            handle=handle,
        )
    if provider == "twscrape" and not (os.getenv("TWSCRAPE_ACCOUNT_DB") or os.getenv("TWSCRAPE_COOKIES")):
        return source_result(
            source,
            "auth_scrape_unconfigured",
            "twscrape is enabled but no operator-provided account database or cookies were configured",
            provider=provider,
            handle=handle,
        )
    if provider == "scweet" and not (os.getenv("SCWEET_AUTH_TOKEN") or os.getenv("SCWEET_COOKIES_FILE")):
        return source_result(
            source,
            "auth_scrape_unconfigured",
            "Scweet is enabled but no operator-provided auth token or cookies file was configured",
            provider=provider,
            handle=handle,
        )
    return source_result(
        source,
        "auth_scrape_not_implemented",
        f"{provider} credentials are configured, but this path is currently an inactive safety stub",
        provider=provider,
        handle=handle,
    )


def archive_x_feed_sources(
    sources: list[dict[str, Any]],
    *,
    raw_root: Path = DEFAULT_RAW_ROOT,
    normalized_root: Path = DEFAULT_NORMALIZED_ROOT,
    providers: str | list[str] | None = None,
    rsshub_base_urls: str | list[str] | None = None,
    nitter_base_urls: str | list[str] | None = None,
    timeout: int = 30,
    max_items: int = 25,
    enable_auth_scrape: bool = False,
    fetcher: Any | None = None,
) -> list[dict[str, Any]]:
    selected_providers = providers_from_value(providers or os.getenv("X_FEED_PROVIDERS", ""))
    rsshub_urls = base_urls_from_value(
        rsshub_base_urls or os.getenv("RSSHUB_BASE_URLS", ""),
        DEFAULT_RSSHUB_BASE_URLS,
    )
    nitter_urls = base_urls_from_value(
        nitter_base_urls or os.getenv("NITTER_BASE_URLS", ""),
        DEFAULT_NITTER_BASE_URLS,
    )
    results: list[dict[str, Any]] = []
    for source in dedupe_x_sources(sources):
        handle = normalize_x_handle(source)
        if not handle:
            results.append(source_result(source, "needs_x_handle", "X feed capture needs an account handle"))
            continue
        for provider in selected_providers:
            if provider in {"twscrape", "scweet"}:
                results.append(archive_auth_scrape_stub(source, provider, handle=handle, enable_auth_scrape=enable_auth_scrape))
                continue
            feed_urls = build_feed_urls(provider, handle, rsshub_base_urls=rsshub_urls, nitter_base_urls=nitter_urls)
            results.append(
                archive_feed_provider(
                    source,
                    provider,
                    handle=handle,
                    raw_root=raw_root,
                    normalized_root=normalized_root,
                    feed_urls=feed_urls,
                    timeout=timeout,
                    max_items=max_items,
                    fetcher=fetcher,
                )
            )
    return results


def feed_urls_for_sources(
    sources: list[dict[str, Any]],
    *,
    providers: str | list[str] | None = None,
    rsshub_base_urls: str | list[str] | None = None,
    nitter_base_urls: str | list[str] | None = None,
) -> list[str]:
    selected_providers = providers_from_value(providers or os.getenv("X_FEED_PROVIDERS", ""))
    rsshub_urls = base_urls_from_value(
        rsshub_base_urls or os.getenv("RSSHUB_BASE_URLS", ""),
        DEFAULT_RSSHUB_BASE_URLS,
    )
    nitter_urls = base_urls_from_value(
        nitter_base_urls or os.getenv("NITTER_BASE_URLS", ""),
        DEFAULT_NITTER_BASE_URLS,
    )
    urls: list[str] = []
    for source in dedupe_x_sources(sources):
        handle = normalize_x_handle(source)
        if not handle:
            continue
        for provider in selected_providers:
            if provider in {"rsshub", "nitter"}:
                urls.extend(build_feed_urls(provider, handle, rsshub_base_urls=rsshub_urls, nitter_base_urls=nitter_urls))
    return urls


def write_newsboat_url_file(path: Path, urls: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(urls).rstrip() + ("\n" if urls else ""), encoding="utf-8")


def select_x_sources(manifest: dict[str, Any], agency_id: str = "") -> list[dict[str, Any]]:
    sources = []
    for source in manifest.get("sources", []):
        if source.get("platform") != "x":
            continue
        if agency_id and source.get("agency_id") != agency_id:
            continue
        sources.append(source)
    return dedupe_x_sources(sources)


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_json(args.manifest)
    selected = select_x_sources(manifest, agency_id=args.agency_id)
    if args.offset_sources:
        selected = selected[int(args.offset_sources) :]
    if args.limit_sources:
        selected = selected[: int(args.limit_sources)]
    newsboat_url_file_value = str(getattr(args, "newsboat_url_file", "") or "")
    newsboat_url_count = 0
    if newsboat_url_file_value:
        newsboat_url_file = Path(newsboat_url_file_value)
        urls = feed_urls_for_sources(
            selected,
            providers=args.x_feed_providers,
            rsshub_base_urls=args.rsshub_base_urls,
            nitter_base_urls=args.nitter_base_urls,
        )
        write_newsboat_url_file(newsboat_url_file, urls)
        newsboat_url_count = len(urls)
    if args.dry_run:
        results = [
            source_result(
                source,
                "would_capture",
                "dry run: X redundant RSSHub/Nitter feed capture",
                handle=normalize_x_handle(source),
            )
            for source in selected
        ]
    else:
        results = archive_x_feed_sources(
            selected,
            raw_root=args.raw_root,
            normalized_root=args.normalized_root,
            providers=args.x_feed_providers,
            rsshub_base_urls=args.rsshub_base_urls,
            nitter_base_urls=args.nitter_base_urls,
            timeout=args.x_feed_timeout,
            max_items=args.x_feed_max_items,
            enable_auth_scrape=args.x_auth_scrape_enabled,
        )
    status_counts = Counter(str(row.get("status") or "unknown") for row in results)
    provider_counts = Counter(str(row.get("provider") or "none") for row in results)
    status_by_provider: dict[str, dict[str, int]] = {}
    for row in results:
        provider = str(row.get("provider") or "none")
        status = str(row.get("status") or "unknown")
        provider_statuses = status_by_provider.setdefault(provider, {})
        provider_statuses[status] = provider_statuses.get(status, 0) + 1
    return {
        "generated_at": now_iso(),
        "dry_run": bool(args.dry_run),
        "inputs": {
            "manifest": str(args.manifest),
            "agency_id": args.agency_id,
            "raw_root": str(args.raw_root),
            "normalized_root": str(args.normalized_root),
            "offset_sources": args.offset_sources,
            "limit_sources": args.limit_sources,
            "x_feed_providers": args.x_feed_providers,
            "rsshub_base_urls": args.rsshub_base_urls,
            "nitter_base_urls": args.nitter_base_urls,
            "x_feed_timeout": args.x_feed_timeout,
            "x_feed_max_items": args.x_feed_max_items,
            "x_auth_scrape_enabled": args.x_auth_scrape_enabled,
            "newsboat_url_file": newsboat_url_file_value,
        },
        "summary": {
            "manifest_x_source_count": len([s for s in manifest.get("sources", []) if s.get("platform") == "x"]),
            "selected_sources": len(selected),
            "status_counts": dict(sorted(status_counts.items())),
            "provider_counts": dict(sorted(provider_counts.items())),
            "status_by_provider": {
                provider: dict(sorted(counts.items()))
                for provider, counts in sorted(status_by_provider.items())
            },
            "newsboat_url_count": newsboat_url_count,
        },
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Archive public X feeds through redundant RSSHub/Nitter-compatible providers.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    parser.add_argument("--normalized-root", type=Path, default=DEFAULT_NORMALIZED_ROOT)
    parser.add_argument("--agency-id", default="")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--offset-sources", type=int, default=0)
    parser.add_argument("--limit-sources", type=int, default=0)
    parser.add_argument("--x-feed-providers", default=os.getenv("X_FEED_PROVIDERS", "rsshub,nitter"))
    parser.add_argument("--rsshub-base-urls", default=os.getenv("RSSHUB_BASE_URLS", ",".join(DEFAULT_RSSHUB_BASE_URLS)))
    parser.add_argument("--nitter-base-urls", default=os.getenv("NITTER_BASE_URLS", ",".join(DEFAULT_NITTER_BASE_URLS)))
    parser.add_argument("--x-feed-timeout", type=int, default=int(os.getenv("X_FEED_TIMEOUT", "30")))
    parser.add_argument("--x-feed-max-items", type=int, default=int(os.getenv("X_FEED_MAX_ITEMS", "25")))
    parser.add_argument("--x-auth-scrape-enabled", action="store_true", default=env_bool("X_AUTH_SCRAPE_ENABLED", False))
    parser.add_argument("--newsboat-url-file", type=Path, default=Path(""))
    args = parser.parse_args()
    report = build_report(args)
    write_json(args.report, report)
    print(json.dumps(report["summary"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
