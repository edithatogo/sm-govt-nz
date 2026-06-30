import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    from scripts.archive_manual_seed import _seed_posts
except ModuleNotFoundError:
    ROOT = Path(__file__).resolve().parents[1]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.archive_manual_seed import _seed_posts

DEFAULT_ROOT = Path("manual_archive_seeds/threads")
THREADS_HOSTS = {"threads.net", "www.threads.net", "threads.com", "www.threads.com"}
KNOWN_SOURCE_HANDLES = {
    "nz-police-threads-newzealandpolice": "newzealandpolice",
    "nzte-threads-nzte": "nzte",
    "wellington-city-libraries-threads-wcl-library": "wcl_library",
    "nz-police": "newzealandpolice",
    "nz-trade-and-enterprise": "nzte",
    "wellington-city-libraries": "wcl_library",
}


def _normalise_handle(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = text.removeprefix("@")
    return re.sub(r"[^a-z0-9._-]", "", text)


def _threads_handle_from_url(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    parsed = urlparse(text)
    if parsed.netloc.lower() not in THREADS_HOSTS:
        return ""
    match = re.search(r"/@([^/?#]+)", parsed.path)
    return _normalise_handle(match.group(1)) if match else ""


def _valid_threads_url(value: Any) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    parsed = urlparse(text)
    return parsed.scheme in {"http", "https"} and parsed.netloc.lower() in THREADS_HOSTS and bool(parsed.path)


def _valid_created_at(value: Any) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    try:
        dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _post_key(post: dict[str, Any]) -> str:
    for field in ("url", "canonical_url", "post_id"):
        value = str(post.get(field) or "").strip()
        if value:
            return f"{field}:{value.lower()}"
    return json.dumps(post, sort_keys=True, ensure_ascii=True)


def validate_seed(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        posts = _seed_posts(payload)
    except Exception as exc:  # noqa: BLE001 - validation report should preserve per-file failures.
        return {
            "path": str(path).replace("\\", "/"),
            "status": "invalid",
            "error": str(exc),
            "record_count": 0,
        }
    errors: list[str] = []
    warnings: list[str] = []
    duplicate_count = 0
    expected_handle = KNOWN_SOURCE_HANDLES.get(path.stem)
    seen: set[str] = set()
    if not expected_handle:
        warnings.append("No known source handle mapping for this seed filename.")
    for index, post in enumerate(posts, start=1):
        key = _post_key(post)
        if key in seen:
            duplicate_count += 1
            errors.append(f"post {index}: duplicate record key {key}")
        seen.add(key)
        url = post.get("url")
        canonical_url = post.get("canonical_url")
        if not _valid_threads_url(url):
            errors.append(f"post {index}: url must be a Threads URL")
        if canonical_url and not _valid_threads_url(canonical_url):
            errors.append(f"post {index}: canonical_url must be a Threads URL when present")
        if not _valid_created_at(post.get("created_at")):
            errors.append(f"post {index}: created_at must be ISO 8601")
        handles = {
            handle for handle in (
                _threads_handle_from_url(url),
                _threads_handle_from_url(canonical_url),
                _normalise_handle(post.get("account")),
            )
            if handle
        }
        if expected_handle and handles and expected_handle not in handles:
            errors.append(
                f"post {index}: expected account @{expected_handle}, found {', '.join(sorted(handles))}"
            )
        media = post.get("media")
        if media is not None and not isinstance(media, list):
            errors.append(f"post {index}: media must be a list when present")
        elif isinstance(media, list):
            for media_index, item in enumerate(media, start=1):
                media_url = item.get("url") if isinstance(item, dict) else item
                if not str(media_url or "").strip():
                    errors.append(f"post {index}: media {media_index} is missing url")
    dates = [str(post.get("created_at") or "") for post in posts if post.get("created_at")]
    status = "invalid" if errors else "valid"
    return {
        "path": str(path).replace("\\", "/"),
        "status": status,
        "record_count": len(posts),
        "duplicate_records": duplicate_count,
        "expected_handle": expected_handle or "",
        "errors": errors,
        "warnings": warnings,
        "min_created_at": min(dates) if dates else "",
        "max_created_at": max(dates) if dates else "",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate authorized Threads manual seed exports.")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--report", type=Path, default=Path("conductor/threads_manual_seed_validation_report.json"))
    parser.add_argument("--allow-empty", action="store_true")
    args = parser.parse_args()

    paths = sorted(
        path for path in args.root.glob("*.json")
        if path.is_file() and not path.name.endswith(".template.json") and path.name != "README.template.json"
    )
    results = [validate_seed(path) for path in paths]
    summary = {
        "seed_files": len(results),
        "valid": sum(1 for result in results if result["status"] == "valid"),
        "invalid": sum(1 for result in results if result["status"] == "invalid"),
        "records": sum(int(result.get("record_count") or 0) for result in results),
        "duplicate_records": sum(int(result.get("duplicate_records") or 0) for result in results),
        "warnings": sum(len(result.get("warnings") or []) for result in results),
    }
    report = {"summary": summary, "results": results}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    if summary["invalid"]:
        raise SystemExit(1)
    if not args.allow_empty and summary["seed_files"] == 0:
        raise SystemExit("No Threads seed files found.")


if __name__ == "__main__":
    main()
