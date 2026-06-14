import json
from typing import Any, Mapping

from scripts.post_threads_latest import run_latest_threads_post
from src.syndication import SyndicationResult


class FakeFeedClient:
    def fetch_author_feed(self, actor: str, *, limit: int = 50) -> list[Mapping[str, Any]]:
        assert actor == "did:plc:agency"
        assert limit == 1
        return [
            {
                "post": {
                    "uri": "at://did:plc:agency/app.bsky.feed.post/post-1",
                    "cid": "cid-post-1",
                    "author": {"did": "did:plc:agency", "handle": "agency.bsky.social"},
                    "record": {"text": "Official update", "createdAt": "2026-06-10T00:00:00Z"},
                    "embed": {"images": []},
                }
            }
        ]


class RecordingThreadsAdapter:
    name = "threads"

    def __init__(self) -> None:
        self.sent_posts = []

    def send(self, post):
        self.sent_posts.append(post)
        return SyndicationResult("threads", success=True, detail="threads-post-id")


def test_dry_run_does_not_mark_delivery(tmp_path, monkeypatch) -> None:
    config_path, backlog_path, delivery_path, archive_dir = write_ready_files(tmp_path)
    monkeypatch.setenv("THREADS_USER_ID", "threads-user")
    monkeypatch.setenv("THREADS_ACCESS_TOKEN", "secret-token")

    result = run_latest_threads_post(
        config_path=str(config_path),
        delivery_state_path=str(delivery_path),
        backlog_state_path=str(backlog_path),
        archive_dir=str(archive_dir),
        dry_run=True,
        feed_client=FakeFeedClient(),
    )

    assert result.dry_run is True
    assert result.skipped is True
    assert result.post_id == "post-1"
    assert json.loads(delivery_path.read_text(encoding="utf-8")) == {"delivered_post_ids": {}}
    assert "<redacted>" in result.detail
    assert "secret-token" not in result.detail


def test_live_run_marks_threads_delivery(tmp_path) -> None:
    config_path, backlog_path, delivery_path, archive_dir = write_ready_files(tmp_path)
    adapter = RecordingThreadsAdapter()

    result = run_latest_threads_post(
        config_path=str(config_path),
        delivery_state_path=str(delivery_path),
        backlog_state_path=str(backlog_path),
        archive_dir=str(archive_dir),
        dry_run=False,
        feed_client=FakeFeedClient(),
        adapter=adapter,
    )

    state = json.loads(delivery_path.read_text(encoding="utf-8"))
    assert result.success is True
    assert result.detail == "threads-post-id"
    assert [post["post_id"] for post in adapter.sent_posts] == ["post-1"]
    assert state["delivered_post_ids"]["threads"]["agency.bsky.social"] == ["post-1"]


def test_live_run_skips_duplicate(tmp_path) -> None:
    config_path, backlog_path, delivery_path, archive_dir = write_ready_files(tmp_path)
    delivery_path.write_text(
        '{"delivered_post_ids": {"threads": {"agency.bsky.social": ["post-1"]}}}',
        encoding="utf-8",
    )

    result = run_latest_threads_post(
        config_path=str(config_path),
        delivery_state_path=str(delivery_path),
        backlog_state_path=str(backlog_path),
        archive_dir=str(archive_dir),
        dry_run=False,
        feed_client=FakeFeedClient(),
        adapter=RecordingThreadsAdapter(),
    )

    assert result.success is True
    assert result.skipped is True
    assert result.detail == "duplicate"


def test_closed_backlog_gate_blocks_posting(tmp_path) -> None:
    config_path, backlog_path, delivery_path, archive_dir = write_ready_files(tmp_path)
    backlog_path.write_text('{"posted_post_ids": {"agency.bsky.social": []}}', encoding="utf-8")

    try:
        run_latest_threads_post(
            config_path=str(config_path),
            delivery_state_path=str(delivery_path),
            backlog_state_path=str(backlog_path),
            archive_dir=str(archive_dir),
            dry_run=False,
            feed_client=FakeFeedClient(),
            adapter=RecordingThreadsAdapter(),
        )
    except RuntimeError as error:
        assert "waiting for Bluesky backlog completion" in str(error)
    else:
        raise AssertionError("Expected closed backlog gate to block Threads posting")


def write_ready_files(tmp_path):
    config_path = tmp_path / "config.json"
    backlog_path = tmp_path / "bluesky_backlog_state.json"
    delivery_path = tmp_path / "target_delivery_state.json"
    archive_dir = tmp_path / "archive"
    account_archive = archive_dir / "agency.bsky.social"
    account_archive.mkdir(parents=True)
    (account_archive / "post-1.json").write_text(
        json.dumps(
            {
                "agency": "agency.bsky.social",
                "post_id": "post-1",
                "created_at": "2026-06-10T00:00:00Z",
                "content": "Official update",
                "source_url": "https://bsky.app/profile/agency.bsky.social/post/post-1",
                "images": [],
                "media_urls": [],
                "edit_history": [],
            }
        ),
        encoding="utf-8",
    )
    config_path.write_text(
        json.dumps(
            {
                "monitored_accounts": [
                    {
                        "handle": "agency.bsky.social",
                        "did": "did:plc:agency",
                        "name": "Agency",
                        "syndicate_to": ["threads"],
                    }
                ],
                "syndication_targets": {
                    "threads": {
                        "enabled": True,
                        "archive_replay_enabled": False,
                        "pipeline_stage_enabled": True,
                        "account_handle": "mirnzcourts",
                        "profile_url": "https://www.threads.com/@mirnzcourts",
                        "gated_by": "bluesky_backlog_complete",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    backlog_path.write_text(
        '{"posted_post_ids": {"agency.bsky.social": ["post-1"]}}',
        encoding="utf-8",
    )
    delivery_path.write_text('{"delivered_post_ids": {}}', encoding="utf-8")
    return config_path, backlog_path, delivery_path, archive_dir
