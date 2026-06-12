import argparse
import datetime as dt
import html
import json
import re
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path
from time import sleep
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.archive_schema import NormalizedArchiveRecord, build_normalized_record, validate_normalized_record


CDX_ENDPOINT = "https://web.archive.org/cdx/search/cdx"
OEMBED_ENDPOINT = "https://publish.twitter.com/oembed"
DEFAULT_CDX_PATTERN = "twitter.com/CourtsofNZ/status/*"
DEFAULT_CDX_PATTERNS = [DEFAULT_CDX_PATTERN, "x.com/CourtsofNZ/status/*"]
TWEET_ID_PATTERN = re.compile(r"/status/(\d+)")


@dataclass(frozen=True)
class TweetCapture:
    tweet_id: str
    original_url: str
    snapshot_timestamp: str
    digest: str


class TweetHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_paragraph = False
        self.paragraph_parts: list[str] = []
        self.link_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "p":
            self.in_paragraph = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "p":
            self.in_paragraph = False

    def handle_data(self, data: str) -> None:
        if self.in_paragraph:
            self.paragraph_parts.append(data)
        else:
            value = data.strip()
            if value:
                self.link_text.append(value)


def fetch_cdx_captures(
    *,
    patterns: list[str] | None = None,
    limit: int = 10000,
) -> list[TweetCapture]:
    captures_by_id: dict[str, TweetCapture] = {}
    for pattern in patterns or DEFAULT_CDX_PATTERNS:
        query = {
            "url": pattern,
            "output": "json",
            "fl": "timestamp,original,statuscode,mimetype,digest",
            "filter": "statuscode:200",
            "collapse": "urlkey",
            "limit": str(limit),
        }
        payload = _fetch_json(f"{CDX_ENDPOINT}?{urlencode(query)}")
        rows = payload[1:] if payload and payload[0][0] == "timestamp" else payload
        for row in rows:
            if not isinstance(row, list) or len(row) < 5:
                continue
            original_url = str(row[1])
            match = TWEET_ID_PATTERN.search(original_url)
            if not match:
                continue
            tweet_id = match.group(1)
            captures_by_id.setdefault(
                tweet_id,
                TweetCapture(
                    tweet_id=tweet_id,
                    original_url=original_url,
                    snapshot_timestamp=str(row[0]),
                    digest=str(row[4]),
                ),
            )
    return sorted(captures_by_id.values(), key=lambda capture: capture.tweet_id)


def fetch_oembed(tweet_id: str) -> dict[str, Any]:
    query = urlencode(
        {
            "url": f"https://twitter.com/CourtsofNZ/status/{tweet_id}",
            "omit_script": "true",
        }
    )
    payload = _fetch_json(f"{OEMBED_ENDPOINT}?{query}")
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid oEmbed payload for tweet {tweet_id}.")
    return payload


def archive_x_history(
    *,
    raw_root: str | Path = "historical_archive_raw/x",
    normalized_root: str | Path = "historical_archive_normalized/x",
    report_path: str | Path = "historical_archive_raw/x/backfill_report.json",
    max_records: int = 0,
    delay_seconds: float = 0.0,
) -> dict[str, Any]:
    captures = fetch_cdx_captures()
    if max_records > 0:
        captures = captures[:max_records]

    normalized_records: list[NormalizedArchiveRecord] = []
    failures: list[dict[str, str]] = []
    reused_raw_count = 0
    fetched_oembed_count = 0
    for capture in captures:
        try:
            existing_raw = _load_existing_raw_payload(capture.tweet_id, raw_root)
            if existing_raw is not None:
                raw_path, payload = existing_raw
                oembed = payload.get("oembed", {})
                reused_raw_count += 1
            else:
                oembed = fetch_oembed(capture.tweet_id)
                raw_path = _write_raw_payload(capture, oembed, raw_root)
                fetched_oembed_count += 1
            record = _normalize_tweet(capture, oembed, raw_path)
            validate_normalized_record(record)
            normalized_records.append(record)
        except Exception as error:
            failures.append({"tweet_id": capture.tweet_id, "error": str(error)})
        if delay_seconds > 0:
            sleep(delay_seconds)

    written_shards = _write_normalized_shards(normalized_records, normalized_root)
    report = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source": {
            "platform": "x",
            "account": "CourtsofNZ",
            "access_method": "internet_archive_cdx_plus_x_oembed",
            "cdx_patterns": DEFAULT_CDX_PATTERNS,
        },
        "cdx_unique_tweet_count": len(captures),
        "archived_count": len(normalized_records),
        "failure_count": len(failures),
        "fetched_oembed_count": fetched_oembed_count,
        "failures": failures,
        "normalized_shards": written_shards,
        "reused_raw_count": reused_raw_count,
    }
    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    Path(report_path).write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def parse_tweet_html(oembed_html: str) -> tuple[str, str]:
    parser = TweetHtmlParser()
    parser.feed(oembed_html)
    text = html.unescape(" ".join(" ".join(parser.paragraph_parts).split()))
    date_text = next((value for value in reversed(parser.link_text) if re.search(r"\d{4}", value)), "")
    return text, _parse_tweet_date(date_text)


def _normalize_tweet(
    capture: TweetCapture,
    oembed: dict[str, Any],
    raw_path: str,
) -> NormalizedArchiveRecord:
    text, created_at = parse_tweet_html(str(oembed.get("html", "")))
    month = created_at[:7] if created_at else _month_from_cdx_timestamp(capture.snapshot_timestamp)
    canonical_url = f"https://x.com/CourtsofNZ/status/{capture.tweet_id}"
    return build_normalized_record(
        record_id=f"x:{capture.tweet_id}",
        agency_id="courts-nz",
        source_platform="x",
        source_account="CourtsofNZ",
        source_kind="inactive_social_archive",
        source_url=str(oembed.get("url") or canonical_url),
        canonical_url=canonical_url,
        original_created_at=created_at,
        captured_at=_datetime_from_cdx_timestamp(capture.snapshot_timestamp),
        content=text,
        raw_path=raw_path,
        extraction_method="internet_archive_cdx_plus_x_oembed",
        cross_source_ids={"tweet_id": capture.tweet_id, "archive_month": month},
    )


def _write_raw_payload(
    capture: TweetCapture,
    oembed: dict[str, Any],
    raw_root: str | Path,
) -> str:
    _, created_at = parse_tweet_html(str(oembed.get("html", "")))
    month = created_at[:7] if created_at else _month_from_cdx_timestamp(capture.snapshot_timestamp)
    path = Path(raw_root) / month / f"{capture.tweet_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"capture": asdict(capture), "oembed": oembed}
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return str(path).replace("\\", "/")


def _load_existing_raw_payload(
    tweet_id: str,
    raw_root: str | Path,
) -> tuple[str, dict[str, Any]] | None:
    root = Path(raw_root)
    if not root.exists():
        return None
    matches = sorted(root.glob(f"*/{tweet_id}.json"))
    if not matches:
        return None
    path = matches[0]
    return str(path).replace("\\", "/"), json.loads(path.read_text(encoding="utf-8"))


def _write_normalized_shards(
    records: list[NormalizedArchiveRecord],
    normalized_root: str | Path,
) -> list[str]:
    by_month: dict[str, list[NormalizedArchiveRecord]] = defaultdict(list)
    for record in records:
        month = record["original_created_at"][:7] or record["captured_at"][:7]
        by_month[month].append(record)

    written: list[str] = []
    root = Path(normalized_root)
    root.mkdir(parents=True, exist_ok=True)
    for month, month_records in sorted(by_month.items()):
        path = root / f"{month}.jsonl"
        with path.open("w", encoding="utf-8") as file:
            for record in sorted(month_records, key=lambda item: item["record_id"]):
                file.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        written.append(str(path).replace("\\", "/"))
    return written


def _parse_tweet_date(value: str) -> str:
    if not value:
        return ""
    try:
        parsed = dt.datetime.strptime(value, "%B %d, %Y").replace(tzinfo=dt.timezone.utc)
        return parsed.isoformat()
    except ValueError:
        return ""


def _datetime_from_cdx_timestamp(value: str) -> str:
    parsed = dt.datetime.strptime(value, "%Y%m%d%H%M%S").replace(tzinfo=dt.timezone.utc)
    return parsed.isoformat()


def _month_from_cdx_timestamp(value: str) -> str:
    return f"{value[:4]}-{value[4:6]}"


def _fetch_json(url: str) -> Any:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "sm-govt-nz-archive/1.0"})
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Archive historical Courts of New Zealand X posts.")
    parser.add_argument("--raw-root", default="historical_archive_raw/x")
    parser.add_argument("--normalized-root", default="historical_archive_normalized/x")
    parser.add_argument("--report", default="historical_archive_raw/x/backfill_report.json")
    parser.add_argument("--max-records", type=int, default=0)
    parser.add_argument("--delay-seconds", type=float, default=0.0)
    args = parser.parse_args()

    report = archive_x_history(
        raw_root=args.raw_root,
        normalized_root=args.normalized_root,
        report_path=args.report,
        max_records=args.max_records,
        delay_seconds=args.delay_seconds,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
