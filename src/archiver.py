import datetime as dt
import json
import os
from pathlib import Path
from typing import Any, Iterable, Optional, TypedDict

from src.bluesky import BlueskyPost


class EditRecord(TypedDict, total=False):
    timestamp: str
    previous_content: str
    previous_media_urls: list[str]
    previous_alt_text: Optional[str]


class PostArchiveSchema(TypedDict, total=False):
    post_id: str
    agency: str
    created_at: str
    content: str
    media_urls: list[str]
    alt_text: Optional[str]
    source_url: str
    images: list[dict[str, str]]
    edit_history: list[EditRecord]


def get_archive_path(
    agency: str,
    post_id: str,
    archive_dir: str | os.PathLike[str] = "historical_archive",
) -> str:
    """Return the JSON archive path for a post."""
    safe_agency = _safe_path_part(agency)
    safe_post_id = _safe_path_part(post_id)
    return str(Path(archive_dir) / safe_agency / f"{safe_post_id}.json")


def load_post_archive(
    agency: str,
    post_id: str,
    archive_dir: str | os.PathLike[str] = "historical_archive",
) -> Optional[PostArchiveSchema]:
    """Load a post archive if it exists."""
    path = Path(get_archive_path(agency, post_id, archive_dir))
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    return _normalize_archive(data)


def archive_post(
    agency: str,
    post_id: str,
    content: str,
    created_at: str,
    media_urls: list[str],
    alt_text: Optional[str] = None,
    archive_dir: str | os.PathLike[str] = "historical_archive",
    source_url: str = "",
    images: list[dict[str, str]] | None = None,
    timestamp: str | None = None,
) -> PostArchiveSchema:
    """Archive a post and append an edit record when post content changes."""
    existing_archive = load_post_archive(agency, post_id, archive_dir)
    path = Path(get_archive_path(agency, post_id, archive_dir))
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized_images = images if images is not None else _images_from_legacy(media_urls, alt_text)

    if existing_archive is not None:
        if _has_changed(existing_archive, content, media_urls, alt_text):
            existing_archive["edit_history"].append(
                {
                    "timestamp": timestamp or _utc_now(),
                    "previous_content": existing_archive["content"],
                    "previous_media_urls": existing_archive.get("media_urls", []),
                    "previous_alt_text": existing_archive.get("alt_text"),
                }
            )
            existing_archive["content"] = content
            existing_archive["media_urls"] = media_urls
            existing_archive["alt_text"] = alt_text
            existing_archive["images"] = normalized_images
            existing_archive["source_url"] = source_url or existing_archive.get("source_url", "")
            _write_json(path, existing_archive)
        return existing_archive

    new_archive: PostArchiveSchema = {
        "post_id": post_id,
        "agency": agency,
        "created_at": created_at,
        "content": content,
        "media_urls": media_urls,
        "alt_text": alt_text,
        "source_url": source_url,
        "images": normalized_images,
        "edit_history": [],
    }
    _write_json(path, new_archive)
    return new_archive


def archive_bluesky_post(
    post: BlueskyPost,
    archive_dir: str | os.PathLike[str] = "historical_archive",
    timestamp: str | None = None,
) -> PostArchiveSchema:
    """Archive a normalized Bluesky post."""
    media_urls = [image["fullsize"] for image in post["images"] if image.get("fullsize")]
    alt_text = "\n".join(image["alt"] for image in post["images"] if image.get("alt")) or None
    return archive_post(
        agency=post["handle"],
        post_id=post["post_id"],
        content=post["text"],
        created_at=post["created_at"],
        media_urls=media_urls,
        alt_text=alt_text,
        archive_dir=archive_dir,
        source_url=post["url"],
        images=post["images"],
        timestamp=timestamp,
    )


def iter_archive_records(
    archive_dir: str | os.PathLike[str] = "historical_archive",
) -> Iterable[PostArchiveSchema]:
    """Yield all archived post records in deterministic path order."""
    root = Path(archive_dir)
    if not root.exists():
        return
    for path in sorted(root.glob("**/*.json")):
        if path.name == "timeline.json":
            continue
        with path.open("r", encoding="utf-8") as file:
            yield _normalize_archive(json.load(file))


def write_timeline(
    archive_dir: str | os.PathLike[str] = "historical_archive",
    output_path: str | os.PathLike[str] | None = None,
) -> list[PostArchiveSchema]:
    """Write a chronological archive timeline for the public dashboard."""
    timeline_path = Path(output_path) if output_path is not None else Path(archive_dir) / "timeline.json"
    records = sorted(
        iter_archive_records(archive_dir),
        key=lambda record: (record.get("created_at", ""), record.get("agency", "")),
        reverse=True,
    )
    _write_json(timeline_path, records)
    return records


def _normalize_archive(data: dict[str, Any]) -> PostArchiveSchema:
    media_urls = [str(item) for item in data.get("media_urls", [])]
    alt_text = data.get("alt_text")
    archive: PostArchiveSchema = {
        "post_id": str(data.get("post_id", "")),
        "agency": str(data.get("agency", "")),
        "created_at": str(data.get("created_at", "")),
        "content": str(data.get("content", "")),
        "media_urls": media_urls,
        "alt_text": str(alt_text) if alt_text is not None else None,
        "source_url": str(data.get("source_url", "")),
        "images": _normalize_images(data.get("images", []), media_urls, alt_text),
        "edit_history": list(data.get("edit_history", [])),
    }
    return archive


def _normalize_images(
    images: Any,
    media_urls: list[str],
    alt_text: Optional[str],
) -> list[dict[str, str]]:
    if isinstance(images, list) and images:
        return [
            {
                "alt": str(image.get("alt", "")),
                "fullsize": str(image.get("fullsize", "")),
                "thumb": str(image.get("thumb", "")),
            }
            for image in images
            if isinstance(image, dict)
        ]
    return _images_from_legacy(media_urls, alt_text)


def _images_from_legacy(media_urls: list[str], alt_text: Optional[str]) -> list[dict[str, str]]:
    return [{"alt": alt_text or "", "fullsize": url, "thumb": ""} for url in media_urls]


def _has_changed(
    archive: PostArchiveSchema,
    content: str,
    media_urls: list[str],
    alt_text: Optional[str],
) -> bool:
    return (
        archive["content"] != content
        or archive.get("media_urls", []) != media_urls
        or archive.get("alt_text") != alt_text
    )


def _safe_path_part(value: str) -> str:
    safe = "".join(char for char in value if char.isalnum() or char in ("-", "_", ".")).strip()
    return safe or "unknown"


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, ensure_ascii=False, sort_keys=True)
        file.write("\n")
