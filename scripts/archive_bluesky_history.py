import argparse
import datetime as dt
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.archiver import archive_bluesky_post, get_archive_path, write_timeline
from src.bluesky import normalize_feed_item


def fetch_author_history(
    actor: str,
    *,
    handle: str,
    limit: int = 100,
    max_pages: int = 100,
    base_url: str = "https://public.api.bsky.app",
) -> list[dict[str, Any]]:
    posts: list[dict[str, Any]] = []
    cursor = ""
    for _ in range(max_pages):
        query = {"actor": actor, "limit": str(limit)}
        if cursor:
            query["cursor"] = cursor
        url = f"{base_url.rstrip('/')}/xrpc/app.bsky.feed.getAuthorFeed?{urlencode(query)}"
        request = Request(url, headers={"Accept": "application/json"})
        with urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
        feed = payload.get("feed", [])
        if not isinstance(feed, list) or not feed:
            break
        for item in feed:
            post = normalize_feed_item(item, handle)
            if post["post_id"]:
                posts.append(dict(post))
        next_cursor = payload.get("cursor")
        if not next_cursor or next_cursor == cursor:
            break
        cursor = str(next_cursor)
    return posts


def build_frequency_report(posts: list[dict[str, Any]]) -> dict[str, Any]:
    dates = [_parse_date(post.get("created_at", "")) for post in posts]
    dates = [date for date in dates if date is not None]
    by_month = Counter(date.strftime("%Y-%m") for date in dates)
    by_year = Counter(date.strftime("%Y") for date in dates)
    by_day = Counter(date.isoformat() for date in dates)
    monthly = [
        {
            "month": month,
            "posts": count,
            "estimated_x_api_cost_with_source_url_usd": round(count * 0.20, 2),
            "estimated_x_api_cost_without_url_usd": round(count * 0.015, 3),
        }
        for month, count in sorted(by_month.items())
    ]
    total_posts = len(dates)
    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "total_posts": total_posts,
        "date_range": {
            "start": min((date.isoformat() for date in dates), default=""),
            "end": max((date.isoformat() for date in dates), default=""),
        },
        "posts_by_year": dict(sorted(by_year.items())),
        "posts_by_month": monthly,
        "daily_average": _daily_average(dates),
        "estimated_total_x_api_cost_with_source_url_usd": round(total_posts * 0.20, 2),
        "estimated_total_x_api_cost_without_url_usd": round(total_posts * 0.015, 3),
        "peak_post_day": _peak_day(by_day),
    }


def build_gap_report(
    posts: list[dict[str, Any]],
    *,
    handle: str,
    archive_dir: str,
) -> dict[str, Any]:
    post_ids = sorted(str(post.get("post_id", "")) for post in posts if post.get("post_id"))
    missing_post_ids = [
        post_id
        for post_id in post_ids
        if not Path(get_archive_path(handle, post_id, archive_dir)).exists()
    ]
    dates = [_parse_date(post.get("created_at", "")) for post in posts]
    dates = [date for date in dates if date is not None]
    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source": {
            "platform": "bluesky",
            "handle": handle,
            "archive_dir": archive_dir,
            "access_method": "public_at_protocol",
        },
        "fetched_count": len(post_ids),
        "archived_count": len(post_ids) - len(missing_post_ids),
        "missing_count": len(missing_post_ids),
        "missing_post_ids": missing_post_ids,
        "date_range": {
            "start": min((date.isoformat() for date in dates), default=""),
            "end": max((date.isoformat() for date in dates), default=""),
        },
    }


def archive_history(
    actor: str,
    *,
    handle: str,
    archive_dir: str,
    report_path: str,
    gap_report_path: str,
    max_pages: int,
) -> dict[str, Any]:
    posts = fetch_author_history(actor, handle=handle, max_pages=max_pages)
    for post in posts:
        archive_bluesky_post(post, archive_dir=archive_dir)
    write_timeline(archive_dir)
    report = build_frequency_report(posts)
    report["source"] = {
        "platform": "bluesky",
        "actor": actor,
        "handle": handle,
        "archive_dir": archive_dir,
    }
    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    Path(report_path).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    gap_report = build_gap_report(posts, handle=handle, archive_dir=archive_dir)
    Path(gap_report_path).parent.mkdir(parents=True, exist_ok=True)
    Path(gap_report_path).write_text(
        json.dumps(gap_report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def _parse_date(value: str) -> dt.date | None:
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _daily_average(dates: list[dt.date]) -> float:
    if not dates:
        return 0.0
    span_days = (max(dates) - min(dates)).days + 1
    return round(len(dates) / span_days, 3)


def _peak_day(by_day: Counter[str]) -> dict[str, Any]:
    if not by_day:
        return {"date": "", "posts": 0}
    date, count = max(by_day.items(), key=lambda item: (item[1], item[0]))
    return {"date": date, "posts": count}


def main() -> None:
    parser = argparse.ArgumentParser(description="Archive public Bluesky author history and report frequency.")
    parser.add_argument("--actor", default="did:plc:vtoa673xlou45zcsj6inyeis")
    parser.add_argument("--handle", default="courtsofnz.bsky.social")
    parser.add_argument("--archive-dir", default="historical_archive")
    parser.add_argument("--report", default="historical_archive/courtsofnz.bsky.social/frequency_report.json")
    parser.add_argument("--gap-report", default="historical_archive/courtsofnz.bsky.social/gap_report.json")
    parser.add_argument("--max-pages", type=int, default=100)
    args = parser.parse_args()

    report = archive_history(
        args.actor,
        handle=args.handle,
        archive_dir=args.archive_dir,
        report_path=args.report,
        gap_report_path=args.gap_report,
        max_pages=args.max_pages,
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
