import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.archive_bluesky_history import fetch_author_history
from scripts.archive_manual_seed import MANUAL_SEED_PLATFORMS, archive_manual_seed, find_manual_seed_path
from src.archive_schema import build_normalized_record


DEFAULT_MANIFEST = Path("conductor/govt_archive_source_manifest.json")
DEFAULT_REPORT = Path("conductor/govt_archive_registered_sources_report.json")
DEFAULT_RAW_ROOT = Path("historical_archive_raw")
DEFAULT_NORMALIZED_ROOT = Path("historical_archive_normalized")
DEFAULT_MANUAL_SEED_ROOT = Path("manual_archive_seeds")
SUPPORTED_PLATFORMS = {"rss", "website_page", "bluesky", *MANUAL_SEED_PLATFORMS}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def stable_id(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def fetch_text(url: str, *, timeout: int = 30) -> str:
    request = Request(
        url,
        headers={"User-Agent": "sm-govt-nz-archive-registered-sources/1.0"},
    )
    with urlopen(request, timeout=timeout) as response:
        return response.read(1_500_000).decode("utf-8", errors="replace")


def month_from_timestamp(value: str) -> str:
    if len(value) >= 7 and value[4] == "-":
        return value[:7]
    return now_iso()[:7]


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


def select_sources(
    sources: list[dict[str, Any]],
    agency_id: str,
    source_type: str,
    only_ready: bool,
) -> list[dict[str, Any]]:
    selected = []
    for source in sources:
        if agency_id and source.get("agency_id") != agency_id:
            continue
        if source_type != "all_feasible" and source.get("platform") != source_type and source.get("source_type") != source_type:
            continue
        if only_ready and source.get("archive_status") not in {"ready", "candidate"}:
            continue
        selected.append(source)
    return selected


def source_result(source: dict[str, Any], status: str, reason: str = "") -> dict[str, Any]:
    return {
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


def archive_website_source(
    source: dict[str, Any],
    raw_root: Path = DEFAULT_RAW_ROOT,
    normalized_root: Path = DEFAULT_NORMALIZED_ROOT,
    website_fetcher: Any | None = None,
) -> dict[str, Any]:
    captured_at = now_iso()
    url = str(source.get("url") or "")
    fetcher = website_fetcher or fetch_text
    html = fetcher(url)
    record_key = stable_id(f"{source.get('source_id')}|{url}")
    raw_rel = Path("website") / captured_at[:7] / f"{record_key}.json"
    raw_path = raw_root / raw_rel
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    if not raw_path.exists():
        raw_path.write_text(
        json.dumps(
            {
                "captured_at": captured_at,
                "source": source,
                "url": url,
                "html": html,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    normalized = build_normalized_record(
        record_id=f"website:{record_key}",
        agency_id=str(source.get("agency_id") or ""),
        source_platform="website_page",
        source_account=str(source.get("account") or source.get("agency_id") or ""),
        source_kind=str(source.get("source_type") or "website_page"),
        source_url=url,
        canonical_url=url,
        original_created_at=captured_at,
        captured_at=captured_at,
        content=html[:100_000],
        raw_path=str(raw_path),
        extraction_method="generic_registered_website_fetch",
        cross_source_ids={"source_id": str(source.get("source_id") or "")},
    )
    inserted = append_normalized_record(normalized_root, "website", normalized)
    return source_result(
        source,
        "captured" if inserted else "already_captured",
        "captured generic website page" if inserted else "website record already present",
    )


def entry_timestamp(entry: dict[str, Any]) -> str:
    for key in ("published", "updated", "created"):
        value = entry.get(key)
        if not value:
            continue
        try:
            return parsedate_to_datetime(str(value)).astimezone(timezone.utc).replace(microsecond=0).isoformat()
        except (TypeError, ValueError, OSError):
            if isinstance(value, str) and value:
                return value
    return now_iso()



def bluesky_handle_from_source(source: dict[str, Any]) -> str:
    account = str(source.get("account") or "").strip()
    if account and "." in account and " " not in account:
        return account.removeprefix("@")
    url = str(source.get("url") or "")
    marker = "/profile/"
    if marker in url:
        return url.split(marker, 1)[1].split("/", 1)[0].removeprefix("@")
    return account.removeprefix("@")


def archive_bluesky_source(
    source: dict[str, Any],
    raw_root: Path = DEFAULT_RAW_ROOT,
    normalized_root: Path = DEFAULT_NORMALIZED_ROOT,
    fetcher: Any | None = None,
    max_pages: int = 1,
) -> list[dict[str, Any]]:
    handle = bluesky_handle_from_source(source)
    if not handle:
        return [source_result(source, "capture_failed", "missing Bluesky handle")]
    fetch = fetcher or fetch_author_history
    posts = fetch(handle, handle=handle, max_pages=max_pages)
    results = []
    for post in posts:
        post_id = str(post.get("post_id") or stable_id(json.dumps(post, sort_keys=True, default=str)))
        created_at = str(post.get("created_at") or now_iso())
        raw_rel = Path("bluesky") / month_from_timestamp(created_at) / f"{post_id}.json"
        raw_path = raw_root / raw_rel
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        if not raw_path.exists():
            raw_path.write_text(
            json.dumps(
                {
                    "captured_at": now_iso(),
                    "source": source,
                    "post": post,
                },
                indent=2,
                sort_keys=True,
                default=str,
            )
            + "\n",
            encoding="utf-8",
        )
        normalized = build_normalized_record(
            record_id=f"bluesky:{post_id}",
            agency_id=str(source.get("agency_id") or ""),
            source_platform="bluesky",
            source_account=handle,
            source_kind=str(source.get("source_type") or "social_profile"),
            source_url=str(source.get("url") or f"https://bsky.app/profile/{handle}"),
            canonical_url=str(post.get("url") or source.get("url") or f"https://bsky.app/profile/{handle}"),
            original_created_at=created_at,
            captured_at=now_iso(),
            content=str(post.get("text") or ""),
            raw_path=str(raw_path),
            extraction_method="generic_registered_bluesky_public_api",
            media_refs=post.get("images") if isinstance(post.get("images"), list) else [],
            cross_source_ids={
                "source_id": str(source.get("source_id") or ""),
                "at_uri": str(post.get("uri") or ""),
                "cid": str(post.get("cid") or ""),
            },
        )
        inserted = append_normalized_record(normalized_root, "bluesky", normalized)
        results.append(
            source_result(
                source,
                "captured" if inserted else "already_captured",
                f"captured bluesky post {normalized['record_id']}" if inserted else "bluesky record already present",
            )
        )
    if not results:
        results.append(source_result(source, "no_records", "Bluesky feed returned no posts"))
    return results






def youtube_channel_id_from_url(url: str) -> str:
    parsed = urlparse(url)
    query_channel_id = parse_qs(parsed.query).get("channel_id", [""])[0]
    if query_channel_id.startswith("UC"):
        return query_channel_id
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) >= 2 and parts[0] == "channel" and parts[1].startswith("UC"):
        return parts[1]
    return ""


def youtube_channel_id_from_page(body: str) -> str:
    patterns = [
        r'"channelId"\s*:\s*"(UC[0-9A-Za-z_-]+)"',
        r'"externalId"\s*:\s*"(UC[0-9A-Za-z_-]+)"',
        r'feeds/videos\.xml\?channel_id=(UC[0-9A-Za-z_-]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, body)
        if match:
            return match.group(1)
    return ""


def resolve_youtube_channel_id(source: dict[str, Any], page_fetcher: Any | None = None) -> str:
    url = str(source.get("url") or "")
    channel_id = youtube_channel_id_from_url(url)
    if channel_id:
        return channel_id
    fetcher = page_fetcher or fetch_text
    page = fetcher(url)
    return youtube_channel_id_from_page(page)


def youtube_feed_url(channel_id: str) -> str:
    return f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"


def archive_youtube_source(
    source: dict[str, Any],
    raw_root: Path = DEFAULT_RAW_ROOT,
    normalized_root: Path = DEFAULT_NORMALIZED_ROOT,
    parser: Any | None = None,
    page_fetcher: Any | None = None,
) -> list[dict[str, Any]]:
    import feedparser

    try:
        channel_id = resolve_youtube_channel_id(source, page_fetcher=page_fetcher)
    except Exception as exc:  # noqa: BLE001 - per-source report records resolver failures.
        return [source_result(source, "capture_failed", f"YouTube channel resolver failed: {str(exc)[:240]}")]
    if not channel_id:
        return [source_result(source, "capture_failed", "could not resolve YouTube channel id")]

    feed_url = youtube_feed_url(channel_id)
    feed_parser = parser or feedparser
    parsed = feed_parser.parse(feed_url)
    results = []
    for entry in getattr(parsed, "entries", []) or []:
        entry_dict = dict(entry)
        video_id = str(entry_dict.get("yt_videoid") or entry_dict.get("id") or "").rsplit(":", 1)[-1]
        link = str(entry_dict.get("link") or (f"https://www.youtube.com/watch?v={video_id}" if video_id else feed_url))
        created_at = entry_timestamp(entry_dict)
        record_key = stable_id(f"{source.get('source_id')}|{channel_id}|{link}|{entry_dict.get('title', '')}")
        raw_rel = Path("youtube") / month_from_timestamp(created_at) / f"{record_key}.json"
        raw_path = raw_root / raw_rel
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        if not raw_path.exists():
            raw_path.write_text(
                json.dumps(
                    {
                        "captured_at": now_iso(),
                        "feed_url": feed_url,
                        "channel_id": channel_id,
                        "source": source,
                        "entry": entry_dict,
                    },
                    indent=2,
                    sort_keys=True,
                    default=str,
                )
                + "\n",
                encoding="utf-8",
            )
        content = "\n\n".join(
            part
            for part in [
                str(entry_dict.get("title") or ""),
                str(entry_dict.get("summary") or entry_dict.get("description") or ""),
            ]
            if part
        )
        normalized = build_normalized_record(
            record_id=f"youtube:{record_key}",
            agency_id=str(source.get("agency_id") or ""),
            source_platform="youtube",
            source_account=str(source.get("account") or channel_id),
            source_kind=str(source.get("source_type") or "social_profile"),
            source_url=str(source.get("url") or feed_url),
            canonical_url=link,
            original_created_at=created_at,
            captured_at=now_iso(),
            content=content,
            raw_path=str(raw_path),
            extraction_method="generic_registered_youtube_channel_rss",
            cross_source_ids={
                "source_id": str(source.get("source_id") or ""),
                "channel_id": channel_id,
                "video_id": video_id,
                "feed_url": feed_url,
            },
        )
        inserted = append_normalized_record(normalized_root, "youtube", normalized)
        results.append(
            source_result(
                source,
                "captured" if inserted else "already_captured",
                f"captured youtube entry {normalized['record_id']}" if inserted else "youtube record already present",
            )
        )
    if not results:
        results.append(source_result(source, "no_records", "YouTube channel RSS returned no entries"))
    return results

def archive_manual_seed_source(
    source: dict[str, Any],
    raw_root: Path = DEFAULT_RAW_ROOT,
    normalized_root: Path = DEFAULT_NORMALIZED_ROOT,
    manual_seed_root: Path = DEFAULT_MANUAL_SEED_ROOT,
) -> list[dict[str, Any]]:
    platform = str(source.get("platform") or "")
    seed_path = find_manual_seed_path(source, manual_seed_root)
    if seed_path is None:
        return [
            source_result(
                source,
                "manual_seed_missing",
                f"{platform} capture requires an operator-authorized seed JSON under manual_archive_seeds/{platform}/",
            )
        ]
    report = archive_manual_seed(
        platform=platform,
        seed_path=seed_path,
        raw_root=raw_root,
        normalized_root=normalized_root,
        agency_id=str(source.get("agency_id") or ""),
        source_account=str(source.get("account") or source.get("url") or ""),
        source_kind=str(source.get("source_type") or "social_profile"),
        source_id=str(source.get("source_id") or ""),
    )
    if int(report.get("record_count", 0)) == 0:
        return [source_result(source, "no_records", f"manual seed contained no {platform} posts: {seed_path}")]
    return [
        source_result(
            source,
            "manual_seed_captured",
            f"captured {report['record_count']} {platform} seed records from {seed_path}",
        )
    ]

def archive_rss_source(
    source: dict[str, Any],
    raw_root: Path = DEFAULT_RAW_ROOT,
    normalized_root: Path = DEFAULT_NORMALIZED_ROOT,
    parser: Any | None = None,
) -> list[dict[str, Any]]:
    import feedparser

    parser = parser or feedparser
    feed_url = str(source.get("url") or "")
    parsed = parser.parse(feed_url)
    results = []
    for entry in getattr(parsed, "entries", []) or []:
        entry_dict = dict(entry)
        link = str(entry_dict.get("link") or entry_dict.get("id") or feed_url)
        created_at = entry_timestamp(entry_dict)
        record_key = stable_id(f"{source.get('source_id')}|{link}|{entry_dict.get('title', '')}")
        raw_rel = Path("rss") / month_from_timestamp(created_at) / f"{record_key}.json"
        raw_path = raw_root / raw_rel
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        if not raw_path.exists():
            raw_path.write_text(
            json.dumps(
                {
                    "captured_at": now_iso(),
                    "feed_url": feed_url,
                    "source": source,
                    "entry": entry_dict,
                },
                indent=2,
                sort_keys=True,
                default=str,
            )
            + "\n",
            encoding="utf-8",
        )
        content = "\n\n".join(
            part
            for part in [
                str(entry_dict.get("title") or ""),
                str(entry_dict.get("summary") or entry_dict.get("description") or ""),
            ]
            if part
        )
        normalized = build_normalized_record(
            record_id=f"rss:{record_key}",
            agency_id=str(source.get("agency_id") or ""),
            source_platform="rss",
            source_account=str(source.get("account") or feed_url),
            source_kind=str(source.get("source_type") or "rss_feed"),
            source_url=feed_url,
            canonical_url=link,
            original_created_at=created_at,
            captured_at=now_iso(),
            content=content,
            raw_path=str(raw_path),
            extraction_method="generic_registered_rss_feedparser",
            cross_source_ids={"source_id": str(source.get("source_id") or "")},
        )
        inserted = append_normalized_record(normalized_root, "rss", normalized)
        results.append(
            source_result(
                source,
                "captured" if inserted else "already_captured",
                f"captured rss entry {normalized['record_id']}" if inserted else "rss record already present",
            )
        )
    if not results:
        results.append(source_result(source, "no_records", "feed parsed but returned no entries"))
    return results


def run_courts_current_sources_if_selected(selected: list[dict[str, Any]], dry_run: bool) -> dict[str, Any] | None:
    courts_sources = [
        source
        for source in selected
        if source.get("agency_id") == "courts-nz" and source.get("platform") in {"bluesky"}
    ]
    if not courts_sources:
        return None
    if dry_run:
        return {"dry_run": True, "selected_supported_courts_sources": len(courts_sources)}
    return {"skipped": True, "reason": "generic Bluesky archiver handles selected Courts sources"}


def capture_registered_source(source: dict[str, Any], args: argparse.Namespace) -> list[dict[str, Any]]:
    raw_root = Path(getattr(args, "raw_root", DEFAULT_RAW_ROOT))
    normalized_root = Path(getattr(args, "normalized_root", DEFAULT_NORMALIZED_ROOT))
    manual_seed_root = Path(getattr(args, "manual_seed_root", DEFAULT_MANUAL_SEED_ROOT))
    platform = source.get("platform")
    if args.dry_run:
        if platform == "youtube":
            return [source_result(source, "would_capture", "dry run: public YouTube channel RSS capture")]
        if platform in MANUAL_SEED_PLATFORMS and find_manual_seed_path(source, manual_seed_root) is None:
            return [source_result(source, "manual_seed_missing", "dry run: manual seed file is not present")]
        return [source_result(source, "would_capture", "dry run")]
    try:
        if platform == "website_page" or source.get("source_type") == "website_page":
            return [archive_website_source(source, raw_root, normalized_root)]
        if platform == "rss" or source.get("source_type") == "rss_feed":
            return archive_rss_source(source, raw_root, normalized_root)
        if platform == "bluesky":
            return archive_bluesky_source(source, raw_root, normalized_root, max_pages=getattr(args, "max_bluesky_pages", 1))
        if platform == "youtube":
            return archive_youtube_source(source, raw_root, normalized_root)
        if platform in MANUAL_SEED_PLATFORMS:
            return archive_manual_seed_source(source, raw_root, normalized_root, manual_seed_root)
    except Exception as exc:  # noqa: BLE001 - archive reports should record per-source failures.
        return [source_result(source, "capture_failed", str(exc)[:300])]
    return [source_result(source, "pending_adapter", "source is feasible but needs a generic adapter or source-specific config before capture")]


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_json(args.manifest)
    selected = select_sources(
        manifest.get("sources", []),
        agency_id=args.agency_id,
        source_type=args.source_type,
        only_ready=not args.include_blocked,
    )
    results = []
    courts_report = run_courts_current_sources_if_selected(selected, args.dry_run)
    for source in selected:
        platform = source.get("platform")
        if platform in SUPPORTED_PLATFORMS or source.get("source_type") in {"rss_feed", "website_page"}:
            results.extend(capture_registered_source(source, args))
        else:
            results.append(
                source_result(
                    source,
                    "unsupported_now",
                    "manifested for onboarding but not captured by the current archive runner",
                )
            )
    status_counts = Counter(row["status"] for row in results)
    platform_counts = Counter(str(source.get("platform") or "unknown") for source in selected)
    status_by_platform: dict[str, dict[str, int]] = {}
    for row in results:
        platform = str(row.get("platform") or "unknown")
        status = str(row.get("status") or "unknown")
        platform_statuses = status_by_platform.setdefault(platform, {})
        platform_statuses[status] = platform_statuses.get(status, 0) + 1
    return {
        "generated_at": now_iso(),
        "dry_run": args.dry_run,
        "inputs": {
            "manifest": str(args.manifest),
            "source_type": args.source_type,
            "agency_id": args.agency_id,
            "include_blocked": args.include_blocked,
            "raw_root": str(getattr(args, "raw_root", DEFAULT_RAW_ROOT)),
            "normalized_root": str(getattr(args, "normalized_root", DEFAULT_NORMALIZED_ROOT)),
            "manual_seed_root": str(getattr(args, "manual_seed_root", DEFAULT_MANUAL_SEED_ROOT)),
        },
        "summary": {
            "selected_sources": len(selected),
            "platform_counts": dict(sorted(platform_counts.items())),
            "status_counts": dict(sorted(status_counts.items())),
            "status_by_platform": {
                platform: dict(sorted(counts.items()))
                for platform, counts in sorted(status_by_platform.items())
            },
        },
        "courts_current_sources_report": courts_report,
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Invoke archive capture for registered government sources.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    parser.add_argument("--normalized-root", type=Path, default=DEFAULT_NORMALIZED_ROOT)
    parser.add_argument("--manual-seed-root", type=Path, default=DEFAULT_MANUAL_SEED_ROOT)
    parser.add_argument(
        "--source-type",
        default="all_feasible",
        choices=["all_feasible", "rss", "website_page", "bluesky", "youtube", "facebook", "instagram", "threads", "linkedin", "newsletter", "x"],
    )
    parser.add_argument("--agency-id", default="")
    parser.add_argument("--include-blocked", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-bluesky-pages", type=int, default=1)
    args = parser.parse_args()

    report = build_report(args)
    write_json(args.report, report)
    print(
        "Archive registered sources report wrote "
        f"{report['summary']['selected_sources']} selected sources."
    )


if __name__ == "__main__":
    main()




