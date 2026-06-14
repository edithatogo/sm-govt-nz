import json

from src.archive_mirror_backlog import run_archive_mirror_backlog
from src.config import AppConfig
from src.syndication import SyndicationResult


def test_archive_mirror_backlog_posts_oldest_x_record(tmp_path) -> None:
    normalized_x_dir = tmp_path / "historical_archive_normalized" / "x"
    normalized_x_dir.mkdir(parents=True)
    write_x_record(normalized_x_dir / "2020-01.jsonl", "x:2", "2020-01-02T00:00:00+00:00")
    write_x_record(normalized_x_dir / "2020-01.jsonl", "x:1", "2020-01-01T00:00:00+00:00")

    adapter = RecordingAdapter()
    summary, next_state = run_archive_mirror_backlog(
        make_config(),
        {"posted_record_ids": {"bluesky": {"x:CourtsofNZ": ["x:1"]}}},
        target="bluesky",
        normalized_archive_dir=tmp_path / "historical_archive_normalized",
        adapters={"bluesky": adapter},
    )

    assert summary.selected == 1
    assert summary.posted == 1
    assert [post["post_id"] for post in adapter.sent_posts] == ["x:2"]
    assert adapter.sent_posts[0]["text"].startswith("Archived X post from 2020-01-02")
    assert next_state["posted_record_ids"]["bluesky"]["x:CourtsofNZ"] == ["x:1", "x:2"]
    assert next_state["posted_records"]["bluesky"]["x:CourtsofNZ"] == [
        {
            "detail": "at://did:plc:mirror/app.bsky.feed.post/x-2",
            "mirror_url": "https://bsky.app/profile/did:plc:mirror/post/x-2",
            "record_id": "x:2",
            "source_key": "x:CourtsofNZ",
            "status": "posted",
            "target": "bluesky",
        }
    ]


def test_archive_mirror_backlog_is_disabled_without_target_flag(tmp_path) -> None:
    config = make_config()
    config["syndication_targets"]["bluesky"]["archive_replay_enabled"] = False

    summary, next_state = run_archive_mirror_backlog(
        config,
        {"posted_record_ids": {}},
        target="bluesky",
        normalized_archive_dir=tmp_path / "historical_archive_normalized",
        dry_run=True,
    )

    assert summary.selected == 0
    assert next_state == {"posted_record_ids": {}}


def test_archive_mirror_backlog_limit_override_controls_batch_size(tmp_path) -> None:
    normalized_x_dir = tmp_path / "historical_archive_normalized" / "x"
    normalized_x_dir.mkdir(parents=True)
    write_x_record(normalized_x_dir / "2020-01.jsonl", "x:1", "2020-01-01T00:00:00+00:00")
    write_x_record(normalized_x_dir / "2020-01.jsonl", "x:2", "2020-01-02T00:00:00+00:00")
    write_x_record(normalized_x_dir / "2020-01.jsonl", "x:3", "2020-01-03T00:00:00+00:00")

    adapter = RecordingAdapter()
    summary, next_state = run_archive_mirror_backlog(
        make_config(),
        {"posted_record_ids": {}},
        target="bluesky",
        normalized_archive_dir=tmp_path / "historical_archive_normalized",
        adapters={"bluesky": adapter},
        limit_override=2,
    )

    assert summary.selected == 2
    assert summary.posted == 2
    assert [post["post_id"] for post in adapter.sent_posts] == ["x:1", "x:2"]
    assert next_state["posted_record_ids"]["bluesky"]["x:CourtsofNZ"] == ["x:1", "x:2"]


def make_config() -> AppConfig:
    return {
        "monitored_accounts": [],
        "syndication_targets": {
            "bluesky": {
                "enabled": True,
                "archive_replay_enabled": True,
                "archive_replay_max_posts_per_run": 1,
                "archive_replay_sources": ["x"],
            }
        },
    }


def write_x_record(path, record_id: str, created_at: str) -> None:
    with path.open("a", encoding="utf-8") as file:
        file.write(
            json.dumps(
                {
                    "record_id": record_id,
                    "source_platform": "x",
                    "source_account": "CourtsofNZ",
                    "original_created_at": created_at,
                    "content": f"Record {record_id}",
                    "source_url": f"https://x.com/CourtsofNZ/status/{record_id.removeprefix('x:')}",
                    "canonical_url": f"https://x.com/CourtsofNZ/status/{record_id.removeprefix('x:')}",
                    "media_refs": [],
                }
            )
            + "\n"
        )


class RecordingAdapter:
    name = "bluesky"

    def __init__(self) -> None:
        self.sent_posts = []

    def send(self, post):
        self.sent_posts.append(post)
        post_key = post["post_id"].replace(":", "-")
        return SyndicationResult(
            "bluesky",
            success=True,
            detail=f"at://did:plc:mirror/app.bsky.feed.post/{post_key}",
        )
