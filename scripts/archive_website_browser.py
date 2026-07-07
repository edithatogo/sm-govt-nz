import argparse
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

from scripts.archive_registered_sources import append_normalized_record, load_json, source_result, stable_id  # noqa: E402
from src.archive_schema import build_normalized_record  # noqa: E402

DEFAULT_MANIFEST = Path("conductor/govt_archive_source_manifest.json")
DEFAULT_TRIAGE_REPORT = Path("conductor/website_archive_failure_triage_report.json")
DEFAULT_REPORT = Path("conductor/website_browser_archive_report.json")
DEFAULT_SUMMARY = Path("conductor/website_browser_archive_summary.md")
DEFAULT_RAW_ROOT = Path("historical_archive_raw")
DEFAULT_NORMALIZED_ROOT = Path("historical_archive_normalized")
ELIGIBLE_STATUSES = {"capture_blocked", "method_not_allowed", "not_acceptable", "network_timeout", "network_error"}
INELIGIBLE_STATUSES = {"dns_failed", "not_found", "tls_failed", "youtube_channel_not_found"}
BLOCKED_MARKERS = [
    ("browser_captcha_or_challenge", re.compile(r"captcha|checking your browser|cloudflare|are you human", re.I)),
    ("browser_access_blocked", re.compile(r"access denied|forbidden|request blocked|not authorised|not authorized", re.I)),
    ("browser_login_required", re.compile(r"sign in|log in|login required|authentication required", re.I)),
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def normalize_space(value: str) -> str:
    return " ".join(value.split())


def html_to_visible_text(html: str) -> str:
    text = re.sub(r"(?is)<(script|style|noscript|svg)\b.*?</\1>", " ", html)
    text = re.sub(r"(?is)<br\s*/?>", "\n", text)
    text = re.sub(r"(?is)</(p|div|section|article|li|h[1-6])>", "\n", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return normalize_space(text)


def detect_browser_status(text: str, html: str) -> tuple[str, str] | None:
    haystack = f"{text}\n{html[:5000]}"
    for status, pattern in BLOCKED_MARKERS:
        match = pattern.search(haystack)
        if match:
            return status, match.group(0)[:120]
    return None


def record_key(source: dict[str, Any]) -> str:
    return stable_id(f"{source.get('source_id')}|{source.get('url')}|website_browser")


def triage_match_key(source: dict[str, Any]) -> str:
    return str(source.get("candidate_id") or source.get("source_id") or "")


def browser_result(source: dict[str, Any], status: str, reason: str, *, raw_path: Path) -> dict[str, Any]:
    result = source_result(source, status, reason)
    result["candidate_id"] = triage_match_key(source)
    result["raw_path"] = str(raw_path).replace("\\", "/")
    return result


def write_raw_capture(
    *,
    source: dict[str, Any],
    captured_at: str,
    final_url: str,
    html: str,
    text: str,
    screenshot_path: str,
    diagnostics: dict[str, Any],
    raw_root: Path,
) -> Path:
    key = record_key(source)
    raw_path = raw_root / "website_browser" / captured_at[:7] / f"{key}.json"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    if not raw_path.exists():
        raw_path.write_text(
            json.dumps(
                {
                    "captured_at": captured_at,
                    "source": source,
                    "url": source.get("url", ""),
                    "final_url": final_url,
                    "html": html,
                    "visible_text": text,
                    "screenshot_path": screenshot_path,
                    "diagnostics": diagnostics,
                    "access_method": "playwright_public_browser_no_login",
                    "guardrails": {
                        "login": False,
                        "captcha_solving": False,
                        "proxies": False,
                        "credential_bypass": False,
                    },
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    return raw_path


def normalize_capture(
    *,
    source: dict[str, Any],
    captured_at: str,
    final_url: str,
    text: str,
    raw_path: Path,
    normalized_root: Path,
) -> bool:
    key = record_key(source)
    record = build_normalized_record(
        record_id=f"website_browser:{key}",
        agency_id=str(source.get("agency_id") or ""),
        source_platform="website_page",
        source_account=str(source.get("account") or source.get("agency_id") or ""),
        source_kind="website_browser_fallback",
        source_url=str(source.get("url") or ""),
        canonical_url=final_url or str(source.get("url") or ""),
        original_created_at=captured_at,
        captured_at=captured_at,
        content=text[:100_000],
        raw_path=str(raw_path).replace("\\", "/"),
        extraction_method="playwright_public_browser_fallback",
        cross_source_ids={"source_id": str(source.get("source_id") or "")},
    )
    return append_normalized_record(normalized_root, "website", record)


def capture_source_with_browser(
    source: dict[str, Any],
    *,
    raw_root: Path,
    normalized_root: Path,
    per_page_timeout: int,
    wait_after_load_ms: int,
    screenshot: bool,
) -> dict[str, Any]:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        try:
            context = browser.new_context(
                user_agent="Mozilla/5.0 (compatible; sm-govt-nz-website-browser-fallback/1.0; +https://github.com/edithatogo/sm-govt-nz)"
            )
            try:
                page = context.new_page()
                page.set_default_timeout(per_page_timeout * 1000)
                captured_at = now_iso()
                started = time.monotonic()
                try:
                    page.goto(str(source.get("url") or ""), wait_until="domcontentloaded", timeout=per_page_timeout * 1000)
                    page.wait_for_timeout(wait_after_load_ms)
                    html = page.content()
                    text = html_to_visible_text(html)
                    final_url = page.url
                    screenshot_path = ""
                    if screenshot:
                        png_path = raw_root / "website_browser" / captured_at[:7] / f"{record_key(source)}.png"
                        png_path.parent.mkdir(parents=True, exist_ok=True)
                        page.screenshot(path=str(png_path), full_page=True, timeout=15_000)
                        screenshot_path = str(png_path).replace("\\", "/")
                    raw_path = write_raw_capture(
                        source=source,
                        captured_at=captured_at,
                        final_url=final_url,
                        html=html,
                        text=text,
                        screenshot_path=screenshot_path,
                        diagnostics={"elapsed_seconds": round(time.monotonic() - started, 2), "visible_text_length": len(text)},
                        raw_root=raw_root,
                    )
                    blocked = detect_browser_status(text, html)
                    if blocked:
                        status, marker = blocked
                        return browser_result(source, status, f"public browser fallback stopped at access marker: {marker}", raw_path=raw_path)
                    if not text:
                        return browser_result(source, "browser_no_visible_content", "public browser fallback produced no visible text", raw_path=raw_path)
                    inserted = normalize_capture(source=source, captured_at=captured_at, final_url=final_url, text=text, raw_path=raw_path, normalized_root=normalized_root)
                    return browser_result(
                        source,
                        "browser_captured" if inserted else "browser_already_captured",
                        "captured public rendered website content" if inserted else "browser website record already present",
                        raw_path=raw_path,
                    )
                except Exception as exc:  # noqa: BLE001 - isolate per-source browser failures.
                    return source_result(source, "browser_capture_failed", str(exc)[:300])
                finally:
                    page.close()
            finally:
                context.close()
        finally:
            browser.close()


def source_is_public_http(source: dict[str, Any]) -> bool:
    parsed = urlparse(str(source.get("url") or ""))
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def load_triage_eligible_source_ids(path: Path, statuses: set[str]) -> tuple[set[str], dict[str, dict[str, Any]]]:
    if not path.exists():
        return set(), {}
    report = load_json(path)
    ids: set[str] = set()
    by_id: dict[str, dict[str, Any]] = {}
    for item in report.get("items", []):
        if not isinstance(item, dict):
            continue
        source_id = str(item.get("source_id") or item.get("candidate_id") or "")
        status = str(item.get("status") or "")
        if source_id and item.get("platform") == "website_page" and status in statuses:
            ids.add(source_id)
            by_id[source_id] = item
    return ids, by_id


def select_sources(
    manifest: dict[str, Any],
    *,
    agency_id: str,
    triage_report: Path,
    eligible_statuses: set[str],
    include_without_triage: bool,
) -> list[dict[str, Any]]:
    eligible_ids, triage_by_id = load_triage_eligible_source_ids(triage_report, eligible_statuses)
    selected = []
    for source in manifest.get("sources", []):
        if agency_id and source.get("agency_id") != agency_id:
            continue
        if source.get("platform") != "website_page" and source.get("source_type") != "website_page":
            continue
        source_id = triage_match_key(source)
        if not source_is_public_http(source):
            continue
        if eligible_ids and source_id not in eligible_ids:
            continue
        if not eligible_ids and not include_without_triage:
            continue
        enriched = dict(source)
        if source_id in triage_by_id:
            trigger = triage_by_id[source_id]
            enriched["browser_fallback_trigger"] = trigger
            enriched["candidate_id"] = str(trigger.get("candidate_id") or source_id)
        selected.append(enriched)
    return selected


def capture_fixture_source(source: dict[str, Any], *, html: str, raw_root: Path, normalized_root: Path) -> dict[str, Any]:
    captured_at = now_iso()
    text = html_to_visible_text(html)
    blocked = detect_browser_status(text, html)
    final_url = str(source.get("url") or "")
    raw_path = write_raw_capture(
        source=source,
        captured_at=captured_at,
        final_url=final_url,
        html=html,
        text=text,
        screenshot_path="",
        diagnostics={"fixture": True, "visible_text_length": len(text)},
        raw_root=raw_root,
    )
    if blocked:
        status, marker = blocked
        return browser_result(source, status, f"public browser fallback stopped at access marker: {marker}", raw_path=raw_path)
    if not text:
        return browser_result(source, "browser_no_visible_content", "public browser fallback produced no visible text", raw_path=raw_path)
    inserted = normalize_capture(source=source, captured_at=captured_at, final_url=final_url, text=text, raw_path=raw_path, normalized_root=normalized_root)
    return browser_result(
        source,
        "browser_captured" if inserted else "browser_already_captured",
        "captured public rendered website content" if inserted else "browser website record already present",
        raw_path=raw_path,
    )


def capture_live_sources(
    sources: list[dict[str, Any]],
    *,
    raw_root: Path,
    normalized_root: Path,
    per_page_timeout: int,
    wait_after_load_ms: int,
    screenshot: bool,
) -> list[dict[str, Any]]:
    return [
        capture_source_with_browser(
            source,
            raw_root=raw_root,
            normalized_root=normalized_root,
            per_page_timeout=per_page_timeout,
            wait_after_load_ms=wait_after_load_ms,
            screenshot=screenshot,
        )
        for source in sources
    ]


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_json(args.manifest)
    eligible_statuses = {status.strip() for status in args.eligible_statuses.split(",") if status.strip()}
    selected = select_sources(
        manifest,
        agency_id=args.agency_id,
        triage_report=args.triage_report,
        eligible_statuses=eligible_statuses,
        include_without_triage=args.include_without_triage,
    )
    offset = int(args.offset_sources or 0)
    if offset > 0:
        selected = selected[offset:]
    limit = int(args.limit_sources or 0)
    if limit > 0:
        selected = selected[:limit]
    if args.dry_run:
        results = [source_result(source, "would_browser_capture", "dry run: eligible public website browser fallback") for source in selected]
    elif args.fixture_html:
        results = [capture_fixture_source(source, html=args.fixture_html, raw_root=args.raw_root, normalized_root=args.normalized_root) for source in selected]
    else:
        results = capture_live_sources(
            selected,
            raw_root=args.raw_root,
            normalized_root=args.normalized_root,
            per_page_timeout=args.per_page_timeout,
            wait_after_load_ms=args.wait_after_load_ms,
            screenshot=args.screenshot,
        )
    status_counts = Counter(str(result.get("status") or "") for result in results)
    return {
        "generated_at": now_iso(),
        "dry_run": bool(args.dry_run),
        "inputs": {
            "manifest": str(args.manifest),
            "triage_report": str(args.triage_report),
            "eligible_statuses": sorted(eligible_statuses),
            "include_without_triage": bool(args.include_without_triage),
            "offset_sources": offset,
            "limit_sources": limit,
            "per_page_timeout": args.per_page_timeout,
            "screenshot": bool(args.screenshot),
        },
        "summary": {
            "selected_sources": len(selected),
            "result_count": len(results),
            "status_counts": dict(sorted(status_counts.items())),
        },
        "guardrails": {
            "login": False,
            "captcha_solving": False,
            "proxies": False,
            "credential_bypass": False,
            "private_api_calls": False,
        },
        "results": results,
    }


def write_summary(path: Path, report: dict[str, Any]) -> None:
    summary = report.get("summary", {})
    lines = [
        "# Website Browser Fallback Archive",
        "",
        f"Generated: {report.get('generated_at', '')}",
        "",
        "## Summary",
        "",
        f"- `selected_sources`: {summary.get('selected_sources', 0)}",
        f"- `result_count`: {summary.get('result_count', 0)}",
        "",
        "## Status counts",
        "",
    ]
    for status, count in summary.get("status_counts", {}).items():
        lines.append(f"- `{status}`: {count}")
    lines.extend([
        "",
        "## Guardrails",
        "",
        "- No login, CAPTCHA solving, proxies, credential bypass, or private API calls.",
        "- Persistent anti-bot/challenge pages are recorded as statuses, not bypassed.",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Archive eligible blocked public website pages with a bounded Playwright browser fallback.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--triage-report", type=Path, default=DEFAULT_TRIAGE_REPORT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    parser.add_argument("--normalized-root", type=Path, default=DEFAULT_NORMALIZED_ROOT)
    parser.add_argument("--agency-id", default="")
    parser.add_argument("--offset-sources", type=int, default=0)
    parser.add_argument("--limit-sources", type=int, default=10)
    parser.add_argument("--eligible-statuses", default=",".join(sorted(ELIGIBLE_STATUSES)))
    parser.add_argument("--include-without-triage", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--fixture-html", default="")
    parser.add_argument("--per-page-timeout", type=int, default=45)
    parser.add_argument("--wait-after-load-ms", type=int, default=2500)
    parser.add_argument("--screenshot", action="store_true")
    args = parser.parse_args()
    report = build_report(args)
    write_json(args.report, report)
    write_summary(args.summary, report)
    print(f"Website browser fallback report wrote {report['summary']['result_count']} results.")


if __name__ == "__main__":
    main()
