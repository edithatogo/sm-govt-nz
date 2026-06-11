import argparse
import json
from pathlib import Path
from typing import Any

from src.archiver import archive_post, get_archive_path, write_timeline


def import_backfill(
    input_path: str | Path,
    archive_dir: str | Path = "historical_archive",
    *,
    mastodon_visibility: str = "unlisted",
) -> list[dict[str, Any]]:
    """Import historical posts from JSON/JSONL without creating live feed spam."""
    imported = []
    for item in _read_items(Path(input_path)):
        agency = str(item.get("agency") or item.get("handle") or "unknown")
        post_id = str(item.get("post_id") or item.get("id") or "")
        if not post_id:
            raise ValueError("Backfill item is missing post_id/id.")
        archived = archive_post(
            agency=agency,
            post_id=post_id,
            content=str(item.get("content") or item.get("text") or ""),
            created_at=str(item.get("created_at") or item.get("createdAt") or ""),
            media_urls=[str(url) for url in item.get("media_urls", [])],
            alt_text=item.get("alt_text"),
            archive_dir=archive_dir,
            source_url=str(item.get("source_url") or item.get("url") or ""),
        )
        archived["backfill"] = True
        archived["mastodon_visibility"] = mastodon_visibility
        _persist_backfill_metadata(agency, post_id, archive_dir, archived)
        imported.append(dict(archived))
    write_timeline(archive_dir)
    return imported


def _read_items(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    payload = json.loads(text)
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("posts"), list):
        return payload["posts"]
    raise ValueError("Backfill input must be a JSON list, {'posts': [...]}, or JSONL.")


def _persist_backfill_metadata(
    agency: str,
    post_id: str,
    archive_dir: str | Path,
    archived: dict[str, Any],
) -> None:
    path = Path(get_archive_path(agency, post_id, archive_dir))
    path.write_text(json.dumps(archived, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import historical post backfills.")
    parser.add_argument("input")
    parser.add_argument("--archive-dir", default="historical_archive")
    parser.add_argument("--mastodon-visibility", default="unlisted")
    args = parser.parse_args()
    imported = import_backfill(
        args.input,
        args.archive_dir,
        mastodon_visibility=args.mastodon_visibility,
    )
    print(json.dumps({"imported": len(imported)}, sort_keys=True))


if __name__ == "__main__":
    main()
