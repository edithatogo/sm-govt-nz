import json

from src.config import AppConfig, BacklogState
from src.threads_pipeline import get_threads_pipeline_status


def test_threads_pipeline_waits_for_bluesky_backlog(tmp_path) -> None:
    archive_dir = tmp_path / "archive" / "courtsofnz.bsky.social"
    archive_dir.mkdir(parents=True)
    write_archive_record(archive_dir, "post-1")
    write_archive_record(archive_dir, "post-2")

    status = get_threads_pipeline_status(
        make_config(),
        {"posted_post_ids": {"courtsofnz.bsky.social": ["post-1"]}},
        archive_dir=str(tmp_path / "archive"),
    )

    assert status.pipeline_stage_enabled is True
    assert status.ready_for_threads_posting is False
    assert status.bluesky_backlog_remaining == 1
    assert "waiting" in status.message


def test_threads_pipeline_reports_ready_after_bluesky_backlog(tmp_path) -> None:
    archive_dir = tmp_path / "archive" / "courtsofnz.bsky.social"
    archive_dir.mkdir(parents=True)
    write_archive_record(archive_dir, "post-1")

    status = get_threads_pipeline_status(
        make_config(),
        {"posted_post_ids": {"courtsofnz.bsky.social": ["post-1"]}},
        archive_dir=str(tmp_path / "archive"),
    )

    assert status.ready_for_threads_posting is True
    assert status.message == "Threads pipeline stage is ready for API credential implementation."


def make_config() -> AppConfig:
    return {
        "monitored_accounts": [
            {
                "handle": "courtsofnz.bsky.social",
                "did": "did:plc:source",
                "name": "Courts",
                "syndicate_to": ["bluesky"],
            }
        ],
        "syndication_targets": {
            "threads": {
                "enabled": False,
                "pipeline_stage_enabled": True,
                "account_handle": "mirnzcourts",
                "profile_url": "https://www.threads.com/@mirnzcourts",
            }
        },
    }


def write_archive_record(directory, post_id: str) -> None:
    (directory / f"{post_id}.json").write_text(
        json.dumps(
            {
                "agency": "courtsofnz.bsky.social",
                "post_id": post_id,
                "created_at": "2026-06-10T00:00:00Z",
                "content": post_id,
                "source_url": f"https://bsky.app/profile/courtsofnz.bsky.social/post/{post_id}",
                "images": [],
                "media_urls": [],
                "edit_history": [],
            }
        ),
        encoding="utf-8",
    )
