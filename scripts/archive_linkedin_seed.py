import argparse
import datetime as dt
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from src.archive_schema import NormalizedArchiveRecord, build_normalized_record


def archive_linkedin_seed(
    *,
    seed_path: str | Path,
    raw_root: str | Path = "historical_archive_raw/linkedin",
    normalized_root: str | Path = "historical_archive_normalized/linkedin",
    report_path: str | Path | None = None,
    captured_at: str | None = None,
) -> dict[str, Any]:
    captured_timestamp = captured_at or dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat()
    seed = json.loads(Path(seed_path).read_text(encoding="utf-8"))
    posts = _seed_posts(seed)
    records = [
        _archive_post(
            post,
            raw_root=Path(raw_root),
            captured_at=captured_timestamp,
        )
        for post in posts
    ]
    _upsert_normalized_records(records, Path(normalized_root))
    report = _build_report(
        seed_path=Path(seed_path),
        records=records,
        captured_at=captured_timestamp,
    )
    if report_path is not None:
        Path(report_path).parent.mkdir(parents=True, exist_ok=True)
        Path(report_path).write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return report


def _seed_posts(seed: Any) -> list[dict[str, Any]]:
    if isinstance(seed, list):
        posts = seed
    elif isinstance(seed, dict):
        posts = seed.get("posts", [])
    else:
        raise ValueError("LinkedIn seed must be a JSON object or array.")
    if not isinstance(posts, list):
        raise ValueError("LinkedIn seed posts must be a list.")
    validated = []
    for index, post in enumerate(posts, start=1):
        if not isinstance(post, dict):
            raise ValueError(f"LinkedIn seed post {index} must be an object.")
        if not str(post.get("text", "")).strip():
            raise ValueError(f"LinkedIn seed post {index} is missing text.")
        if not str(post.get("url", "")).strip():
            raise ValueError(f"LinkedIn seed post {index} is missing url.")
        if not str(post.get("created_at", "")).strip():
            raise ValueError(f"LinkedIn seed post {index} is missing created_at.")
        validated.append(post)
    return validated


def _archive_post(
    post: dict[str, Any],
    *,
    raw_root: Path,
    captured_at: str,
) -> NormalizedArchiveRecord:
    post_id = str(post.get("post_id") or _stable_post_id(post))
    created_at = str(post["created_at"])
    month = _month_from_datetime(created_at)
    raw_path = raw_root / month / f"{_safe_id(post_id)}.json"
    raw_payload = {
        "captured_at": captured_at,
        "source": "linkedin_manual_seed",
        "post": post,
    }
    existing_captured_at = _existing_captured_at(raw_path)
    if not raw_path.exists():
        _write_json_if_changed(raw_path, raw_payload)

    url = str(post["url"])
    return build_normalized_record(
        record_id=f"linkedin:{post_id}",
        agency_id="courts-nz",
        source_platform="linkedin",
        source_account=str(post.get("account") or "Courts of New Zealand"),
        source_kind="social_feed",
        source_url=url,
        canonical_url=str(post.get("canonical_url") or url),
        original_created_at=created_at,
        captured_at=existing_captured_at or captured_at,
        content=str(post["text"]),
        raw_path=str(raw_path).replace("\\", "/"),
        extraction_method="manual_seed",
        media_refs=_media_refs(post),
        cross_source_ids={
            "linkedin_post_id": post_id,
            "seed_url": url,
        },
    )


def _media_refs(post: dict[str, Any]) -> list[dict[str, str]]:
    media = post.get("media", [])
    if not isinstance(media, list):
        return []
    refs = []
    for item in media:
        if isinstance(item, str):
            refs.append({"url": item, "media_type": "unknown", "alt_text": ""})
        elif isinstance(item, dict) and item.get("url"):
            refs.append(
                {
                    "url": str(item.get("url", "")),
                    "media_type": str(item.get("media_type", "unknown")),
                    "alt_text": str(item.get("alt_text", "")),
                }
            )
    return refs


def _upsert_normalized_records(records: list[NormalizedArchiveRecord], normalized_root: Path) -> None:
    by_month: dict[str, list[NormalizedArchiveRecord]] = defaultdict(list)
    for record in records:
        by_month[_month_from_datetime(record["original_created_at"])].append(record)

    for month, month_records in by_month.items():
        shard_path = normalized_root / f"{month}.jsonl"
        existing, order = _load_shard(shard_path)
        for record in month_records:
            previous = existing.get(record["record_id"])
            if previous and previous.get("content_hash") == record["content_hash"]:
                record["captured_at"] = str(previous.get("captured_at", record["captured_at"]))
            if record["record_id"] not in existing:
                order.append(record["record_id"])
            existing[record["record_id"]] = record
        _write_jsonl_if_changed(shard_path, existing, order)


def _load_shard(path: Path) -> tuple[dict[str, NormalizedArchiveRecord], list[str]]:
    if not path.exists():
        return {}, []
    records: dict[str, NormalizedArchiveRecord] = {}
    order = []
    for line in path.read_text(encoding="utf-8").splitlines():
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
    order: list[str],
) -> None:
    lines = [json.dumps(records[record_id], ensure_ascii=False, sort_keys=True) for record_id in order]
    content = "\n".join(lines) + ("\n" if lines else "")
    _write_text_if_changed(path, content)


def _write_json_if_changed(path: Path, payload: dict[str, Any]) -> None:
    _write_text_if_changed(
        path,
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
    )


def _write_text_if_changed(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return
    path.write_text(content, encoding="utf-8")


def _existing_captured_at(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ""
    return str(payload.get("captured_at", ""))


def _build_report(
    *,
    seed_path: Path,
    records: list[NormalizedArchiveRecord],
    captured_at: str,
) -> dict[str, Any]:
    dates = [record["original_created_at"] for record in records if record.get("original_created_at")]
    return {
        "source": "linkedin",
        "access_method": "manual_seed",
        "archive_only": True,
        "seed_path": str(seed_path).replace("\\", "/"),
        "captured_at": captured_at,
        "record_count": len(records),
        "min_original_created_at": min(dates) if dates else "",
        "max_original_created_at": max(dates) if dates else "",
        "gaps": [
            "Manual seed coverage depends on the operator-authorized export or bounded browser capture supplied as input."
        ],
    }


def _stable_post_id(post: dict[str, Any]) -> str:
    payload = f"{post.get('url', '')}\n{post.get('created_at', '')}\n{post.get('text', '')}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def _month_from_datetime(value: str) -> str:
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.date().strftime("%Y-%m")
    except ValueError:
        return dt.datetime.now(dt.UTC).date().strftime("%Y-%m")


def _safe_id(value: str) -> str:
    safe = "".join(char for char in value if char.isalnum() or char in ("-", "_", ".")).strip()
    return safe or "unknown"


def main() -> None:
    parser = argparse.ArgumentParser(description="Archive a Courts NZ LinkedIn manual seed export.")
    parser.add_argument("--seed-json", required=True)
    parser.add_argument("--raw-root", default="historical_archive_raw/linkedin")
    parser.add_argument("--normalized-root", default="historical_archive_normalized/linkedin")
    parser.add_argument("--report", default="conductor/linkedin_archive_report.json")
    args = parser.parse_args()

    report = archive_linkedin_seed(
        seed_path=args.seed_json,
        raw_root=args.raw_root,
        normalized_root=args.normalized_root,
        report_path=args.report,
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
