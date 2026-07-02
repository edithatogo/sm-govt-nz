import argparse
import hashlib
import json
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.archive_schema import build_normalized_record  # noqa: E402


DEFAULT_MANIFEST = Path("conductor/govt_archive_source_manifest.json")
DEFAULT_REPORT = Path("conductor/x_browser_archive_report.json")
DEFAULT_RAW_ROOT = Path("historical_archive_raw")
DEFAULT_NORMALIZED_ROOT = Path("historical_archive_normalized")
TWEET_URL_PATTERN = re.compile(r"https?://(?:www\.)?(?:x|twitter)\.com/([^/?#]+)/status/(\d+)")
RELATIVE_TWEET_URL_PATTERN = re.compile(r"^/([^/?#]+)/status/(\d+)")
BLOCKED_MARKERS = [
    ("protected", "These posts are protected"),
    ("login_required", "Sign in to X"),
    ("not_found", "This account doesn"),
    ("not_found", "This profile does not exist"),
    ("not_found", "Account doesn"),
    ("suspended", "Account suspended"),
    ("rate_limited", "Rate limit exceeded"),
    ("temporarily_unavailable", "Something went wrong"),
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def stable_id(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def month_from_timestamp(value: str) -> str:
    if len(value) >= 7 and value[4] == "-":
        return value[:7]
    return now_iso()[:7]


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def normalize_x_handle(source: dict[str, Any]) -> str:
    account = str(source.get("account") or "").strip().lstrip("@")
    lowered = account.lower()
    if lowered.startswith("twitter.com/") or lowered.startswith("x.com/"):
        account = account.split("/", 1)[1]
    if account and "/" not in account and " " not in account and "." not in account:
        return account.strip().lstrip("@")
    parsed = urlparse(str(source.get("url") or ""))
    host = parsed.netloc.lower()
    if host not in {"x.com", "www.x.com", "twitter.com", "www.twitter.com"}:
        return ""
    parts = [part for part in parsed.path.split("/") if part]
    if not parts or parts[0].lower() in {"home", "share", "intent", "i", "search"}:
        return ""
    return parts[0].strip().lstrip("@")


def dedupe_x_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_handle: dict[str, dict[str, Any]] = {}
    for source in sources:
        handle = normalize_x_handle(source)
        if not handle:
            continue
        key = handle.lower()
        existing = by_handle.get(key)
        candidate = dict(source)
        candidate["account"] = handle
        candidate["browser_capture_handle"] = handle
        if not str(candidate.get("url") or "").strip():
            candidate["url"] = f"https://x.com/{handle}"
        if existing is None:
            candidate["duplicate_source_ids"] = [str(source.get("source_id") or "")]
            candidate["duplicate_urls"] = [str(source.get("url") or "")]
            by_handle[key] = candidate
            continue
        existing["duplicate_source_ids"].append(str(source.get("source_id") or ""))
        existing["duplicate_urls"].append(str(source.get("url") or ""))
        if existing.get("archive_status") != "ready" and candidate.get("archive_status") == "ready":
            candidate["duplicate_source_ids"] = existing["duplicate_source_ids"]
            candidate["duplicate_urls"] = existing["duplicate_urls"]
            by_handle[key] = candidate
    return sorted(by_handle.values(), key=lambda item: str(item.get("browser_capture_handle") or "").lower())


def select_x_browser_sources(manifest: dict[str, Any], agency_id: str = "") -> list[dict[str, Any]]:
    selected = []
    for source in manifest.get("sources", []):
        if source.get("platform") != "x":
            continue
        if agency_id and source.get("agency_id") != agency_id:
            continue
        selected.append(source)
    return dedupe_x_sources(selected)


def detect_blocked_status(text: str) -> tuple[str, str] | None:
    for status, marker in BLOCKED_MARKERS:
        if marker.lower() in text.lower():
            return status, marker
    return None


def canonicalize_tweet_url(value: str) -> tuple[str, str]:
    match = TWEET_URL_PATTERN.search(value)
    if match:
        return f"https://x.com/{match.group(1)}/status/{match.group(2)}", match.group(2)
    relative = RELATIVE_TWEET_URL_PATTERN.search(value)
    if relative:
        return f"https://x.com/{relative.group(1)}/status/{relative.group(2)}", relative.group(2)
    return "", ""


def post_from_card(card: Any, *, handle: str, index: int) -> dict[str, Any] | None:
    try:
        text = " ".join(str(card.inner_text(timeout=1500) or "").split())
    except Exception:
        text = ""
    try:
        outer_html = str(card.evaluate("node => node.outerHTML") or "")
    except Exception:
        outer_html = ""
    try:
        hrefs = card.locator("a").evaluate_all(
            "els => [...new Set(els.map(a => a.href || a.getAttribute('href') || '').filter(Boolean))]"
        )
    except Exception:
        hrefs = []
    try:
        media = card.locator("img, video").evaluate_all(
            """els => [...els].map(el => ({
                url: el.currentSrc || el.src || el.getAttribute('poster') || '',
                media_type: el.tagName === 'VIDEO' ? 'video' : 'image',
                alt_text: el.getAttribute('alt') || el.getAttribute('aria-label') || ''
            })).filter(item => item.url)"""
        )
    except Exception:
        media = []
    try:
        card_links = card.locator("a").evaluate_all(
            """els => [...els].map(a => ({
                url: a.href || a.getAttribute('href') || '',
                text: (a.innerText || a.getAttribute('aria-label') || '').replace(/\s+/g, ' ').trim()
            })).filter(item => item.url)"""
        )
    except Exception:
        card_links = []
    external_links = [
        str(href)
        for href in hrefs
        if href and not re.search(r"https?://(?:www\.)?(?:x|twitter)\.com/", str(href), flags=re.I)
    ]
    try:
        created_at = str(card.locator("time").first.get_attribute("datetime", timeout=1000) or "")
    except Exception:
        created_at = ""
    canonical_url = ""
    tweet_id = ""
    for href in hrefs:
        canonical_url, tweet_id = canonicalize_tweet_url(str(href))
        if tweet_id:
            break
    if not tweet_id:
        fingerprint = stable_id(f"{handle}|{index}|{text}|{outer_html[:500]}")
        tweet_id = f"visible-{fingerprint}"
        canonical_url = f"https://x.com/{handle}"
    if not text and not outer_html:
        return None
    return {
        "tweet_id": tweet_id,
        "canonical_url": canonical_url,
        "created_at": created_at or now_iso(),
        "text": text,
        "html": outer_html,
        "hrefs": hrefs,
        "external_links": external_links,
        "card_links": card_links,
        "media": media,
    }


def extract_posts_from_page(page: Any, *, handle: str) -> list[dict[str, Any]]:
    posts_by_id: dict[str, dict[str, Any]] = {}
    cards = page.locator('[data-testid="tweet"]')
    try:
        count = cards.count()
    except Exception:
        count = 0
    for index in range(count):
        post = post_from_card(cards.nth(index), handle=handle, index=index)
        if post:
            posts_by_id.setdefault(str(post["tweet_id"]), post)
    return list(posts_by_id.values())


def extract_posts_from_html(html: str, *, handle: str) -> list[dict[str, Any]]:
    posts = []
    seen: set[str] = set()
    for match in re.finditer(r"(?:https?://(?:www\.)?(?:x|twitter)\.com|)/([^/?#]+)/status/(\d+)", html):
        if match.group(1).lower() in {"i", "intent", "share"}:
            continue
        tweet_id = match.group(2)
        if tweet_id in seen:
            continue
        seen.add(tweet_id)
        posts.append(
            {
                "tweet_id": tweet_id,
                "canonical_url": f"https://x.com/{match.group(1)}/status/{tweet_id}",
                "created_at": now_iso(),
                "text": "",
                "html": "",
                "hrefs": [match.group(0)],
                "external_links": [],
                "card_links": [],
                "media": [],
            }
        )
    if not posts and html.strip():
        posts.append(
            {
                "tweet_id": f"visible-{stable_id(handle + html[:1000])}",
                "canonical_url": f"https://x.com/{handle}",
                "created_at": now_iso(),
                "text": " ".join(re.sub(r"<[^>]+>", " ", html).split())[:4000],
                "html": html,
                "hrefs": [],
                "external_links": [],
                "card_links": [],
                "media": [],
            }
        )
    return posts


def append_normalized_record(root: Path, platform: str, record: dict[str, Any]) -> bool:
    shard = root / platform / f"{month_from_timestamp(record['original_created_at'])}.jsonl"
    shard.parent.mkdir(parents=True, exist_ok=True)
    existing_ids: set[str] = set()
    if shard.exists():
        for line in shard.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                existing_ids.add(str(json.loads(line).get("record_id", "")))
            except json.JSONDecodeError:
                continue
    if record["record_id"] in existing_ids:
        return False
    with shard.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return True


def write_browser_raw(
    *,
    raw_root: Path,
    source: dict[str, Any],
    handle: str,
    captured_at: str,
    html: str,
    posts: list[dict[str, Any]],
    screenshot_path: str,
    diagnostics: dict[str, Any],
) -> Path:
    key = stable_id(f"{source.get('source_id')}|{handle}|{captured_at[:10]}")
    raw_path = raw_root / "x_browser" / captured_at[:7] / f"{handle.lower()}_{key}.json"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(
        json.dumps(
            {
                "captured_at": captured_at,
                "source": source,
                "handle": handle,
                "url": f"https://x.com/{handle}",
                "html": html,
                "posts": posts,
                "screenshot_path": screenshot_path,
                "diagnostics": diagnostics,
                "policy": {
                    "access_method": "seleniumbase_playwright_public_browser",
                    "no_login": True,
                    "no_proxy": True,
                    "no_captcha_solving": True,
                    "no_private_graphql": True,
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


def normalize_browser_posts(
    *,
    source: dict[str, Any],
    handle: str,
    posts: list[dict[str, Any]],
    raw_path: Path,
    normalized_root: Path,
    captured_at: str,
) -> tuple[int, int]:
    captured = 0
    already = 0
    for post in posts:
        tweet_id = str(post.get("tweet_id") or stable_id(json.dumps(post, sort_keys=True)))
        created_at = str(post.get("created_at") or captured_at)
        content = str(post.get("text") or "")
        if not content:
            content = "Visible X browser post captured; text was not available in rendered card."
        record = build_normalized_record(
            record_id=f"x_browser:{tweet_id}",
            agency_id=str(source.get("agency_id") or ""),
            source_platform="x",
            source_account=handle,
            source_kind="public_browser_visible_post",
            source_url=f"https://x.com/{handle}",
            canonical_url=str(post.get("canonical_url") or f"https://x.com/{handle}"),
            original_created_at=created_at,
            captured_at=captured_at,
            content=content,
            raw_path=str(raw_path).replace("\\", "/"),
            extraction_method="seleniumbase_playwright_public_browser",
            media_refs=[
                {
                    "url": str(item.get("url") or ""),
                    "media_type": str(item.get("media_type") or ""),
                    "alt_text": str(item.get("alt_text") or ""),
                }
                for item in post.get("media", [])
                if isinstance(item, dict) and item.get("url")
            ],
            cross_source_ids={
                "source_id": str(source.get("source_id") or ""),
                "duplicate_source_ids": ",".join(source.get("duplicate_source_ids", [])),
                "x_username": handle,
                "x_post_id": tweet_id,
                "external_links": ",".join(str(link) for link in post.get("external_links", []) if link),
                "card_link_count": str(len(post.get("card_links", []))),
                "media_count": str(len(post.get("media", []))),
            },
        )
        if append_normalized_record(normalized_root, "x", record):
            captured += 1
        else:
            already += 1
    return captured, already


class BrowserSession:
    def __init__(self) -> None:
        self.sb = None
        self.playwright = None
        self.browser = None
        self.page = None

    def __enter__(self) -> "BrowserSession":
        from playwright.sync_api import sync_playwright
        from seleniumbase import sb_cdp

        last_error: Exception | None = None
        for attempt in range(3):
            try:
                self.sb = sb_cdp.Chrome()
                endpoint_url = self.sb.get_endpoint_url()
                self.playwright = sync_playwright().start()
                self.browser = self.playwright.chromium.connect_over_cdp(endpoint_url, timeout=60_000)
                context = self.browser.contexts[0] if self.browser.contexts else self.browser.new_context()
                self.page = context.pages[0] if context.pages else context.new_page()
                self.page.set_default_timeout(15_000)
                return self
            except Exception as exc:  # noqa: BLE001 - browser startup can be transient under Xvfb.
                last_error = exc
                self.__exit__(None, None, None)
                time.sleep(5 * (attempt + 1))
        raise RuntimeError(f"Failed to start SeleniumBase CDP browser after retries: {last_error}")

    def __exit__(self, *_exc: object) -> None:
        for item in [self.browser, self.playwright, self.sb]:
            try:
                if hasattr(item, "close"):
                    item.close()
                elif hasattr(item, "stop"):
                    item.stop()
                elif hasattr(item, "quit"):
                    item.quit()
            except Exception:
                pass


def capture_source_with_browser(
    source: dict[str, Any],
    *,
    session: BrowserSession,
    raw_root: Path,
    normalized_root: Path,
    max_scrolls: int,
    idle_rounds: int,
    per_account_timeout: int,
) -> dict[str, Any]:
    handle = str(source.get("browser_capture_handle") or normalize_x_handle(source))
    if not handle:
        return source_result(source, "needs_x_handle", "X browser capture needs an account handle")
    page = session.page
    captured_at = now_iso()
    started = time.monotonic()
    url = f"https://x.com/{handle}"
    page.goto(url, wait_until="domcontentloaded", timeout=per_account_timeout * 1000)
    page.wait_for_timeout(3500)
    seen_ids: set[str] = set()
    posts: list[dict[str, Any]] = []
    idle = 0
    for _round in range(max_scrolls + 1):
        for post in extract_posts_from_page(page, handle=handle):
            tweet_id = str(post.get("tweet_id") or "")
            if tweet_id and tweet_id not in seen_ids:
                seen_ids.add(tweet_id)
                posts.append(post)
        if time.monotonic() - started > per_account_timeout:
            break
        previous_count = len(seen_ids)
        page.mouse.wheel(0, 2600)
        page.wait_for_timeout(1800)
        for post in extract_posts_from_page(page, handle=handle):
            tweet_id = str(post.get("tweet_id") or "")
            if tweet_id and tweet_id not in seen_ids:
                seen_ids.add(tweet_id)
                posts.append(post)
        if len(seen_ids) == previous_count:
            idle += 1
            if idle >= idle_rounds:
                break
        else:
            idle = 0
    html = page.content()
    blocked = detect_blocked_status(page.inner_text("body", timeout=3000) if page.locator("body").count() else html)
    screenshot_path = ""
    screenshot = raw_root / "x_browser" / captured_at[:7] / f"{handle.lower()}_{captured_at[:10]}.png"
    try:
        screenshot.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(screenshot), full_page=True, timeout=15_000)
        screenshot_path = str(screenshot).replace("\\", "/")
    except Exception:
        screenshot_path = ""
    raw_path = write_browser_raw(
        raw_root=raw_root,
        source=source,
        handle=handle,
        captured_at=captured_at,
        html=html,
        posts=posts,
        screenshot_path=screenshot_path,
        diagnostics={
            "max_scrolls": max_scrolls,
            "idle_rounds": idle_rounds,
            "elapsed_seconds": round(time.monotonic() - started, 2),
            "visible_post_count": len(posts),
            "blocked_status": blocked[0] if blocked else "",
        },
    )
    captured_count, already_count = normalize_browser_posts(
        source=source,
        handle=handle,
        posts=posts,
        raw_path=raw_path,
        normalized_root=normalized_root,
        captured_at=captured_at,
    )
    if posts:
        status = "browser_posts_captured" if captured_count else "browser_posts_already_captured"
        reason = f"visible_posts={len(posts)} captured={captured_count} already={already_count}"
    elif blocked:
        status, marker = blocked
        reason = f"public browser page did not expose posts: {marker}"
    else:
        status = "browser_no_visible_posts"
        reason = "public browser page loaded but no visible post cards were found"
    return source_result(source, status, reason, handle=handle, raw_path=str(raw_path).replace("\\", "/"))


def capture_source_from_fixture(
    source: dict[str, Any],
    *,
    html: str,
    raw_root: Path,
    normalized_root: Path,
) -> dict[str, Any]:
    handle = str(source.get("browser_capture_handle") or normalize_x_handle(source))
    captured_at = now_iso()
    posts = extract_posts_from_html(html, handle=handle)
    raw_path = write_browser_raw(
        raw_root=raw_root,
        source=source,
        handle=handle,
        captured_at=captured_at,
        html=html,
        posts=posts,
        screenshot_path="",
        diagnostics={"fixture": True, "visible_post_count": len(posts)},
    )
    captured_count, already_count = normalize_browser_posts(
        source=source,
        handle=handle,
        posts=posts,
        raw_path=raw_path,
        normalized_root=normalized_root,
        captured_at=captured_at,
    )
    return source_result(
        source,
        "browser_posts_captured" if captured_count else "browser_posts_already_captured",
        f"fixture visible_posts={len(posts)} captured={captured_count} already={already_count}",
        handle=handle,
        raw_path=str(raw_path).replace("\\", "/"),
    )


def source_result(source: dict[str, Any], status: str, reason: str = "", **extra: Any) -> dict[str, Any]:
    payload = {
        "source_id": source.get("source_id"),
        "agency_id": source.get("agency_id"),
        "platform": source.get("platform"),
        "source_type": source.get("source_type"),
        "url": source.get("url"),
        "archive_status": source.get("archive_status"),
        "feasibility": source.get("feasibility"),
        "status": status,
        "reason": reason,
    }
    payload.update(extra)
    return payload


def archive_x_browser_sources(
    sources: list[dict[str, Any]],
    *,
    raw_root: Path = DEFAULT_RAW_ROOT,
    normalized_root: Path = DEFAULT_NORMALIZED_ROOT,
    max_scrolls: int = 25,
    idle_rounds: int = 3,
    per_account_timeout: int = 120,
    fixture_html: str = "",
) -> list[dict[str, Any]]:
    deduped = dedupe_x_sources(sources)
    if fixture_html:
        return [
            capture_source_from_fixture(source, html=fixture_html, raw_root=raw_root, normalized_root=normalized_root)
            for source in deduped
        ]
    results = []
    with BrowserSession() as session:
        for source in deduped:
            try:
                results.append(
                    capture_source_with_browser(
                        source,
                        session=session,
                        raw_root=raw_root,
                        normalized_root=normalized_root,
                        max_scrolls=max_scrolls,
                        idle_rounds=idle_rounds,
                        per_account_timeout=per_account_timeout,
                    )
                )
            except Exception as exc:  # noqa: BLE001 - per-source report must isolate failures.
                results.append(source_result(source, "browser_capture_failed", str(exc)[:300], handle=normalize_x_handle(source)))
    return results


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_json(args.manifest)
    selected = select_x_browser_sources(manifest, agency_id=args.agency_id)
    offset_sources = int(args.offset_sources or 0)
    if offset_sources > 0:
        selected = selected[offset_sources:]
    limit_sources = int(args.limit_sources or 0)
    if limit_sources > 0:
        selected = selected[:limit_sources]
    if args.dry_run:
        results = [
            source_result(source, "would_capture", "dry run: SeleniumBase/Playwright public browser capture", handle=normalize_x_handle(source))
            for source in selected
        ]
    else:
        fixture_html = Path(args.fixture_html).read_text(encoding="utf-8") if args.fixture_html else ""
        results = archive_x_browser_sources(
            selected,
            raw_root=args.raw_root,
            normalized_root=args.normalized_root,
            max_scrolls=args.max_scrolls,
            idle_rounds=args.idle_rounds,
            per_account_timeout=args.per_account_timeout,
            fixture_html=fixture_html,
        )
    status_counts = Counter(str(row.get("status") or "unknown") for row in results)
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
            "max_scrolls": args.max_scrolls,
            "idle_rounds": args.idle_rounds,
            "per_account_timeout": args.per_account_timeout,
            "fixture_html": str(args.fixture_html or ""),
        },
        "summary": {
            "manifest_x_source_count": len([s for s in manifest.get("sources", []) if s.get("platform") == "x"]),
            "selected_sources": len(selected),
            "status_counts": dict(sorted(status_counts.items())),
        },
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Archive public X pages via SeleniumBase/Playwright browser capture.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    parser.add_argument("--normalized-root", type=Path, default=DEFAULT_NORMALIZED_ROOT)
    parser.add_argument("--agency-id", default="")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--offset-sources", type=int, default=0)
    parser.add_argument("--limit-sources", type=int, default=0)
    parser.add_argument("--max-scrolls", type=int, default=25)
    parser.add_argument("--idle-rounds", type=int, default=3)
    parser.add_argument("--per-account-timeout", type=int, default=120)
    parser.add_argument("--fixture-html", default="")
    args = parser.parse_args()
    report = build_report(args)
    write_json(args.report, report)
    print(json.dumps(report["summary"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
