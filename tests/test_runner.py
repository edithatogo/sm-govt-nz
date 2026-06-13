import json
from typing import Any, Mapping

from src.config import AppConfig, AppState
from src.runner import run_syndication
from src.syndication import DryRunAdapter


class FakeFeedClient:
    def fetch_author_feed(self, actor: str, *, limit: int = 50) -> list[Mapping[str, Any]]:
        return [
            make_feed_item("post-2", "Newest"),
            make_feed_item("post-1", "Older"),
        ]


class FailingFeedClient:
    def fetch_author_feed(self, actor: str, *, limit: int = 50) -> list[Mapping[str, Any]]:
        raise AssertionError("Feed should not be fetched without active account targets")


def test_runner_fetches_posts_sends_to_enabled_targets_and_updates_state(tmp_path) -> None:
    config = make_config()
    state: AppState = {"last_seen_post_ids": {"agency.bsky.social": ""}}
    discord = DryRunAdapter("discord")
    mastodon = DryRunAdapter("mastodon")

    summary, next_state = run_syndication(
        config,
        state,
        feed_client=FakeFeedClient(),
        adapters={"discord": discord, "mastodon": mastodon},
        archive_dir=str(tmp_path / "archive"),
    )

    assert summary.fetched == 2
    assert [post["post_id"] for post in discord.sent_posts] == ["post-1", "post-2"]
    assert [post["post_id"] for post in mastodon.sent_posts] == ["post-1", "post-2"]
    assert next_state["last_seen_post_ids"]["agency.bsky.social"] == "post-2"
    assert (tmp_path / "archive" / "agency.bsky.social" / "post-2.json").exists()


def test_runner_dry_run_does_not_advance_state() -> None:
    config = make_config()
    state: AppState = {"last_seen_post_ids": {"agency.bsky.social": "post-0"}}

    _, next_state = run_syndication(
        config,
        state,
        feed_client=FakeFeedClient(),
        adapters={"discord": DryRunAdapter("discord")},
        dry_run=True,
    )

    assert next_state == state


def test_runner_rejects_enabled_target_without_adapter() -> None:
    config = make_config()
    config["syndication_targets"]["x"] = {"enabled": True}
    state: AppState = {"last_seen_post_ids": {"agency.bsky.social": ""}}

    try:
        run_syndication(
            config,
            state,
            feed_client=FakeFeedClient(),
            adapters={"discord": DryRunAdapter("discord"), "mastodon": DryRunAdapter("mastodon")},
        )
    except RuntimeError as error:
        assert "x" in str(error)
    else:
        raise AssertionError("Expected missing X adapter to fail before state can advance")


def test_runner_limits_posts_before_advancing_state(tmp_path) -> None:
    config = make_config()
    config["monitored_accounts"][0]["syndicate_to"] = ["bluesky"]
    config["syndication_targets"] = {
        "bluesky": {"enabled": True, "max_posts_per_run": 1},
    }
    state: AppState = {"last_seen_post_ids": {"agency.bsky.social": ""}}
    adapter = DryRunAdapter("bluesky")

    summary, next_state = run_syndication(
        config,
        state,
        feed_client=FakeFeedClient(),
        adapters={"bluesky": adapter},
        archive_dir=str(tmp_path / "archive"),
    )

    assert summary.fetched == 1
    assert [post["post_id"] for post in adapter.sent_posts] == ["post-1"]
    assert next_state["last_seen_post_ids"]["agency.bsky.social"] == "post-1"
    assert not (tmp_path / "archive" / "agency.bsky.social" / "post-2.json").exists()


def test_runner_does_not_fetch_or_advance_when_threads_gate_is_closed(tmp_path) -> None:
    config = make_config()
    config["monitored_accounts"][0]["syndicate_to"] = ["threads"]
    config["syndication_targets"] = {
        "threads": {
            "enabled": True,
            "max_posts_per_run": 1,
            "pipeline_stage_enabled": True,
            "account_handle": "mirnzcourts",
            "profile_url": "https://www.threads.com/@mirnzcourts",
            "gated_by": "bluesky_backlog_complete",
        },
    }
    archive_dir = tmp_path / "archive"
    account_dir = archive_dir / "agency.bsky.social"
    account_dir.mkdir(parents=True)
    write_archive_record(account_dir, "post-1")
    backlog_state_path = tmp_path / "bluesky_backlog_state.json"
    backlog_state_path.write_text('{"posted_post_ids": {"agency.bsky.social": []}}', encoding="utf-8")
    state: AppState = {"last_seen_post_ids": {"agency.bsky.social": "post-0"}}

    summary, next_state = run_syndication(
        config,
        state,
        feed_client=FailingFeedClient(),
        adapters={},
        backlog_state_path=str(backlog_state_path),
        backlog_archive_dir=str(archive_dir),
    )

    assert summary.fetched == 0
    assert summary.syndicated == 0
    assert next_state == state


def make_config() -> AppConfig:
    return {
        "monitored_accounts": [
            {
                "handle": "agency.bsky.social",
                "did": "did:plc:agency",
                "name": "Agency",
                "syndicate_to": ["discord", "mastodon", "x"],
            }
        ],
        "syndication_targets": {
            "discord": {"enabled": True},
            "mastodon": {"enabled": True},
            "x": {"enabled": False},
        },
    }


def make_feed_item(post_id: str, text: str) -> Mapping[str, Any]:
    return {
        "post": {
            "uri": f"at://did:plc:agency/app.bsky.feed.post/{post_id}",
            "cid": f"cid-{post_id}",
            "author": {"did": "did:plc:agency", "handle": "agency.bsky.social"},
            "record": {"text": text, "createdAt": "2026-06-10T00:00:00Z"},
            "embed": {"images": []},
        }
    }


def write_archive_record(directory, post_id: str) -> None:
    (directory / f"{post_id}.json").write_text(
        json.dumps(
            {
                "agency": "agency.bsky.social",
                "post_id": post_id,
                "created_at": "2026-06-10T00:00:00Z",
                "content": post_id,
                "source_url": f"https://bsky.app/profile/agency.bsky.social/post/{post_id}",
                "images": [],
                "media_urls": [],
                "edit_history": [],
            }
        ),
        encoding="utf-8",
    )
