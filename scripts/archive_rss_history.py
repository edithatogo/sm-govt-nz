import argparse
import datetime as dt
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Protocol

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.archive_schema import NormalizedArchiveRecord, build_normalized_record, validate_normalized_record
from src.feed_ingestion import normalize_feed_entry


class FeedParserModule(Protocol):
    def parse(self, url: str) -> Any:
        """Parse a feed URL into a feedparser-compatible object."""


def archive_rss_history(
    *,
    feed_report_path: str | Path = "config/courts-of-nz_rss_feeds.json",
    raw_root: str | Path = "historical_archive_raw/rss",
    normalized_root: str | Path = "historical_archive_normalized/rss",
    report_path: str | Path = "historical_archive_raw/rss/backfill_report.json",
    parser: FeedParserModule | None = None,
) -> dict[str, Any]:
    feeds = json.loads(Path(feed_report_path).read_text(encoding="utf-8")).get("feeds", [])
    feed_parser = parser or _load_feedparser()
    normalized_records: list[NormalizedArchiveRecord] = []
    feed_reports: list[dict[str, Any]] = []

    for feed in feeds:
        feed_url = str(feed["feed_url"])
        try:
            parsed = feed_parser.parse(feed_url)
            entries = list(getattr(parsed, "entries", []))
            feed_records = [
                _archive_entry(entry, feed_url=feed_url, raw_root=raw_root)
                for entry in entries
            ]
            normalized_records.extend(feed_records)
            feed_reports.append(
                {
                    "feed_url": feed_url,
                    "status": "healthy",
                    "entry_count": len(entries),
                    "archived_count": len(feed_records),
                    "error": "",
                }
            )
        except Exception as error:
            feed_reports.append(
                {
                    "feed_url": feed_url,
                    "status": "unavailable",
                    "entry_count": 0,
                    "archived_count": 0,
                    "error": str(error),
                }
            )

    written_shards = _write_normalized_shards(normalized_records, normalized_root)
    report = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source": {
            "platform": "rss",
            "access_method": "feedparser",
            "feed_report_path": str(feed_report_path),
        },
        "feed_count": len(feeds),
        "archived_count": len(normalized_records),
        "feeds": feed_reports,
        "normalized_shards": written_shards,
    }
    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    Path(report_path).write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def _archive_entry(
    entry: Any,
    *,
    feed_url: str,
    raw_root: str | Path,
) -> NormalizedArchiveRecord:
    post = normalize_feed_entry(entry, source_id="courtsofnz.govt.nz", feed_url=feed_url)
    month = _month_from_created_at(post["created_at"])
    record_id = _rss_record_id(feed_url, post["url"], post["text"])
    raw_path = Path(raw_root) / month / f"{record_id}.json"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_payload = {
        "feed_url": feed_url,
        "entry": _json_safe(entry),
    }
    raw_path.write_text(
        json.dumps(raw_payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    record = build_normalized_record(
        record_id=f"rss:{record_id}",
        agency_id="courts-nz",
        source_platform="rss",
        source_account="courtsofnz.govt.nz",
        source_kind="rss_entry",
        source_url=feed_url,
        canonical_url=post["url"],
        original_created_at=post["created_at"],
        captured_at=dt.datetime.now(dt.timezone.utc).isoformat(),
        content=post["text"],
        raw_path=str(raw_path).replace("\\", "/"),
        extraction_method="feedparser",
        cross_source_ids={"feed_url": feed_url, "feed_entry_id": post["post_id"]},
    )
    validate_normalized_record(record)
    return record


def _write_normalized_shards(
    records: list[NormalizedArchiveRecord],
    normalized_root: str | Path,
) -> list[str]:
    by_month: dict[str, list[NormalizedArchiveRecord]] = defaultdict(list)
    for record in records:
        by_month[_month_from_created_at(record["original_created_at"])].append(record)

    root = Path(normalized_root)
    root.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for month, month_records in sorted(by_month.items()):
        path = root / f"{month}.jsonl"
        with path.open("w", encoding="utf-8") as file:
            for record in sorted(month_records, key=lambda item: item["record_id"]):
                file.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        written.append(str(path).replace("\\", "/"))
    return written


def _rss_record_id(feed_url: str, entry_url: str, text: str) -> str:
    value = f"{feed_url}\n{entry_url}\n{text}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def _month_from_created_at(value: str) -> str:
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.date().strftime("%Y-%m")
    except ValueError:
        return dt.datetime.now(dt.timezone.utc).date().strftime("%Y-%m")


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Archive Courts of New Zealand RSS feed histories.")
    parser.add_argument("--feed-report", default="config/courts-of-nz_rss_feeds.json")
    parser.add_argument("--raw-root", default="historical_archive_raw/rss")
    parser.add_argument("--normalized-root", default="historical_archive_normalized/rss")
    parser.add_argument("--report", default="historical_archive_raw/rss/backfill_report.json")
    args = parser.parse_args()

    report = archive_rss_history(
        feed_report_path=args.feed_report,
        raw_root=args.raw_root,
        normalized_root=args.normalized_root,
        report_path=args.report,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
