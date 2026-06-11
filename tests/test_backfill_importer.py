import json

from scripts.backfill_importer import import_backfill


def test_import_backfill_archives_posts_with_unlisted_visibility(tmp_path) -> None:
    input_path = tmp_path / "backfill.json"
    archive_dir = tmp_path / "archive"
    input_path.write_text(
        json.dumps(
            [
                {
                    "agency": "agency.bsky.social",
                    "post_id": "old-1",
                    "content": "Historical post",
                    "created_at": "2025-01-01T00:00:00Z",
                    "source_url": "https://example.test/old-1",
                }
            ]
        ),
        encoding="utf-8",
    )

    imported = import_backfill(input_path, archive_dir, mastodon_visibility="unlisted")

    archive_path = archive_dir / "agency.bsky.social" / "old-1.json"
    timeline_path = archive_dir / "timeline.json"
    saved = json.loads(archive_path.read_text(encoding="utf-8"))
    timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
    assert imported[0]["backfill"] is True
    assert saved["mastodon_visibility"] == "unlisted"
    assert timeline[0]["post_id"] == "old-1"
