import json

from src.bluesky_backlog import run_bluesky_backlog
from src.config import AppConfig, BacklogState
from src.bluesky import BlueskyPost
from src.syndication import SyndicationResult


def test_bluesky_backlog_posts_oldest_unposted_record_and_updates_separate_state(tmp_path) -> None:
    archive_dir = tmp_path / "archive"
    account_dir = archive_dir / "agency.bsky.social"
    account_dir.mkdir(parents=True)
    write_archive_record(account_dir, "post-2", "2026-06-11T00:00:00Z", "Second")
    write_archive_record(account_dir, "post-1", "2026-06-10T00:00:00Z", "First")

    adapter = RecordingAdapter()
    state: BacklogState = {"posted_post_ids": {"agency.bsky.social": ["post-1"]}}

    summary, next_state = run_bluesky_backlog(
        make_config(),
        state,
        archive_dir=str(archive_dir),
        adapters={"bluesky": adapter},
    )

    assert summary.selected == 1
    assert [post["post_id"] for post in adapter.sent_posts] == ["post-2"]
    assert next_state["posted_post_ids"]["agency.bsky.social"] == ["post-1", "post-2"]


def test_bluesky_backlog_dry_run_does_not_advance_state(tmp_path) -> None:
    archive_dir = tmp_path / "archive"
    account_dir = archive_dir / "agency.bsky.social"
    account_dir.mkdir(parents=True)
    write_archive_record(account_dir, "post-1", "2026-06-10T00:00:00Z", "First")

    state: BacklogState = {"posted_post_ids": {}}
    summary, next_state = run_bluesky_backlog(
        make_config(),
        state,
        archive_dir=str(archive_dir),
        dry_run=True,
    )

    assert summary.selected == 1
    assert summary.posted == 0
    assert next_state == state


def test_bluesky_backlog_is_disabled_without_explicit_flag(tmp_path) -> None:
    config = make_config()
    config["syndication_targets"]["bluesky"]["backlog_enabled"] = False

    summary, next_state = run_bluesky_backlog(
        config,
        {"posted_post_ids": {}},
        archive_dir=str(tmp_path / "archive"),
        dry_run=True,
    )

    assert summary.selected == 0
    assert next_state == {"posted_post_ids": {}}


def make_config() -> AppConfig:
    return {
        "monitored_accounts": [
            {
                "handle": "agency.bsky.social",
                "did": "did:plc:agency",
                "name": "Agency",
                "syndicate_to": ["bluesky"],
            }
        ],
        "syndication_targets": {
            "bluesky": {
                "enabled": True,
                "max_posts_per_run": 1,
                "backlog_enabled": True,
                "backlog_max_posts_per_run": 1,
                "backlog_order": "oldest_first",
            }
        },
    }


def write_archive_record(directory, post_id: str, created_at: str, content: str) -> None:
    (directory / f"{post_id}.json").write_text(
        json.dumps(
            {
                "agency": "agency.bsky.social",
                "post_id": post_id,
                "created_at": created_at,
                "content": content,
                "source_url": f"https://bsky.app/profile/agency.bsky.social/post/{post_id}",
                "images": [],
                "media_urls": [],
                "edit_history": [],
            }
        ),
        encoding="utf-8",
    )


class RecordingAdapter:
    name = "bluesky"

    def __init__(self) -> None:
        self.sent_posts: list[BlueskyPost] = []

    def send(self, post: BlueskyPost) -> SyndicationResult:
        self.sent_posts.append(post)
        return SyndicationResult("bluesky", success=True, detail=f"mirror-{post['post_id']}")
