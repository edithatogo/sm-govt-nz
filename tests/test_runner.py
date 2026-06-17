import json
from typing import Any, Mapping

from src.config import AppConfig, AppState
from src.runner import run_syndication
from src.syndication import DryRunAdapter, SyndicationResult


class FakeFeedClient:
    def fetch_author_feed(self, actor: str, *, limit: int = 50) -> list[Mapping[str, Any]]:
        return [
            make_feed_item("post-2", "Newest"),
            make_feed_item("post-1", "Older"),
        ]


class FailingFeedClient:
    def fetch_author_feed(self, actor: str, *, limit: int = 50) -> list[Mapping[str, Any]]:
        raise AssertionError("Feed should not be fetched without active account targets")


class EmptyFeedClient:
    def fetch_author_feed(self, actor: str, *, limit: int = 50) -> list[Mapping[str, Any]]:
        return []


class FailingAdapter:
    name = "threads"

    def send(self, post):
        return SyndicationResult(self.name, success=False, detail="remote failure")


class RaisingAdapter:
    name = "threads"

    def send(self, post):
        raise RuntimeError("remote unavailable")


class RecordingSuccessAdapter:
    def __init__(self, name: str) -> None:
        self.name = name
        self.sent_posts = []

    def send(self, post):
        self.sent_posts.append(post)
        return SyndicationResult(self.name, success=True, detail=f"{self.name}-{post['post_id']}")


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


def test_runner_isolates_enabled_target_without_adapter(tmp_path) -> None:
    config = make_config()
    config["syndication_targets"]["x"] = {"enabled": True}
    state: AppState = {"last_seen_post_ids": {"agency.bsky.social": ""}}
    delivery_state = {"delivered_post_ids": {}}
    discord = DryRunAdapter("discord")
    mastodon = DryRunAdapter("mastodon")

    summary, next_state = run_syndication(
        config,
        state,
        feed_client=FakeFeedClient(),
        adapters={"discord": discord, "mastodon": mastodon},
        archive_dir=str(tmp_path / "archive"),
        delivery_state=delivery_state,
    )

    missing_target_results = [result for result in summary.accounts[0].results if result.platform == "x"]
    assert missing_target_results
    assert all(not result.success for result in missing_target_results)
    assert all(result.skipped for result in missing_target_results)
    assert [post["post_id"] for post in discord.sent_posts] == ["post-1", "post-2"]
    assert [post["post_id"] for post in mastodon.sent_posts] == ["post-1", "post-2"]
    assert next_state["last_seen_post_ids"]["agency.bsky.social"] == "post-2"
    assert delivery_state["pending_post_ids"]["x"]["agency.bsky.social"] == ["post-1", "post-2"]
    assert (tmp_path / "archive" / "agency.bsky.social" / "post-1.json").exists()
    assert (tmp_path / "archive" / "agency.bsky.social" / "post-2.json").exists()


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


def test_runner_skips_target_duplicate_from_delivery_state(tmp_path) -> None:
    config = make_config()
    config["monitored_accounts"][0]["syndicate_to"] = ["bluesky", "threads"]
    config["syndication_targets"] = {
        "bluesky": {"enabled": True},
        "threads": {"enabled": True},
    }
    state: AppState = {"last_seen_post_ids": {"agency.bsky.social": ""}}
    delivery_state = {
        "delivered_post_ids": {
            "threads": {"agency.bsky.social": ["post-1"]},
        }
    }
    bluesky = RecordingSuccessAdapter("bluesky")
    threads = RecordingSuccessAdapter("threads")

    summary, next_state = run_syndication(
        config,
        state,
        feed_client=FakeFeedClient(),
        adapters={"bluesky": bluesky, "threads": threads},
        archive_dir=str(tmp_path / "archive"),
        delivery_state=delivery_state,
    )

    assert summary.fetched == 2
    assert [post["post_id"] for post in threads.sent_posts] == ["post-2"]
    assert delivery_state["delivered_post_ids"]["threads"]["agency.bsky.social"] == [
        "post-1",
        "post-2",
    ]
    assert next_state["last_seen_post_ids"]["agency.bsky.social"] == "post-2"


def test_runner_tracks_instagram_delivery_separately(tmp_path) -> None:
    config = make_config()
    config["monitored_accounts"][0]["syndicate_to"] = ["bluesky", "instagram"]
    config["syndication_targets"] = {
        "bluesky": {"enabled": True, "max_posts_per_run": 1},
        "instagram": {"enabled": True, "max_posts_per_run": 1},
    }
    state: AppState = {"last_seen_post_ids": {"agency.bsky.social": ""}}
    delivery_state = {"delivered_post_ids": {}}
    bluesky = RecordingSuccessAdapter("bluesky")
    instagram = RecordingSuccessAdapter("instagram")

    _summary, next_state = run_syndication(
        config,
        state,
        feed_client=FakeFeedClient(),
        adapters={"bluesky": bluesky, "instagram": instagram},
        archive_dir=str(tmp_path / "archive"),
        delivery_state=delivery_state,
    )

    assert [post["post_id"] for post in instagram.sent_posts] == ["post-1"]
    assert delivery_state["delivered_post_ids"]["instagram"]["agency.bsky.social"] == ["post-1"]
    assert delivery_state["delivered_post_ids"]["bluesky"]["agency.bsky.social"] == ["post-1"]
    assert next_state["last_seen_post_ids"]["agency.bsky.social"] == "post-1"


def test_runner_wires_unified_transparency_adapter_from_base_target(tmp_path) -> None:
    config = make_config()
    config["monitored_accounts"][0]["syndicate_to"] = ["unified"]
    config["syndication_targets"] = {
        "bluesky": {"enabled": False},
        "unified": {"enabled": True, "base_target": "bluesky", "max_posts_per_run": 1},
    }
    state: AppState = {"last_seen_post_ids": {"agency.bsky.social": ""}}
    delivery_state = {"delivered_post_ids": {}}
    bluesky = RecordingSuccessAdapter("bluesky")

    _summary, next_state = run_syndication(
        config,
        state,
        feed_client=FakeFeedClient(),
        adapters={"bluesky": bluesky},
        archive_dir=str(tmp_path / "archive"),
        delivery_state=delivery_state,
    )

    assert [post["post_id"] for post in bluesky.sent_posts] == ["post-1"]
    assert bluesky.sent_posts[0]["text"] == "[Agency] Older"
    assert delivery_state["delivered_post_ids"]["unified"]["agency.bsky.social"] == ["post-1"]
    assert next_state["last_seen_post_ids"]["agency.bsky.social"] == "post-1"


def test_runner_does_not_advance_source_state_when_target_delivery_fails(tmp_path) -> None:
    config = make_config()
    config["monitored_accounts"][0]["syndicate_to"] = ["bluesky", "threads"]
    config["syndication_targets"] = {
        "bluesky": {"enabled": True, "max_posts_per_run": 1},
        "threads": {"enabled": True, "max_posts_per_run": 1},
    }
    state: AppState = {"last_seen_post_ids": {"agency.bsky.social": ""}}
    delivery_state = {"delivered_post_ids": {}}
    bluesky = RecordingSuccessAdapter("bluesky")

    _summary, next_state = run_syndication(
        config,
        state,
        feed_client=FakeFeedClient(),
        adapters={"bluesky": bluesky, "threads": FailingAdapter()},
        archive_dir=str(tmp_path / "archive"),
        delivery_state=delivery_state,
    )

    assert [post["post_id"] for post in bluesky.sent_posts] == ["post-1"]
    assert delivery_state["delivered_post_ids"]["bluesky"]["agency.bsky.social"] == ["post-1"]
    assert "threads" not in delivery_state["delivered_post_ids"]
    assert next_state == state


def test_runner_isolates_target_adapter_exceptions(tmp_path) -> None:
    config = make_config()
    config["monitored_accounts"][0]["syndicate_to"] = ["bluesky", "threads"]
    config["syndication_targets"] = {
        "bluesky": {"enabled": True, "max_posts_per_run": 1},
        "threads": {"enabled": True, "max_posts_per_run": 1},
    }
    state: AppState = {"last_seen_post_ids": {"agency.bsky.social": ""}}
    delivery_state = {"delivered_post_ids": {}}
    bluesky = RecordingSuccessAdapter("bluesky")

    summary, next_state = run_syndication(
        config,
        state,
        feed_client=FakeFeedClient(),
        adapters={"bluesky": bluesky, "threads": RaisingAdapter()},
        archive_dir=str(tmp_path / "archive"),
        delivery_state=delivery_state,
    )

    assert [post["post_id"] for post in bluesky.sent_posts] == ["post-1"]
    assert delivery_state["delivered_post_ids"]["bluesky"]["agency.bsky.social"] == ["post-1"]
    assert "threads" not in delivery_state["delivered_post_ids"]
    assert next_state == state
    assert summary.accounts[0].results[-1].platform == "threads"
    assert summary.accounts[0].results[-1].success is False
    assert "RuntimeError: remote unavailable" in summary.accounts[0].results[-1].detail


def test_runner_x_failure_does_not_block_source_state_or_other_targets(tmp_path) -> None:
    config = make_config()
    config["monitored_accounts"][0]["syndicate_to"] = ["bluesky", "x"]
    config["syndication_targets"] = {
        "bluesky": {"enabled": True, "max_posts_per_run": 1},
        "x": {"enabled": True, "max_posts_per_run": 1},
    }
    state: AppState = {"last_seen_post_ids": {"agency.bsky.social": ""}}
    delivery_state = {"delivered_post_ids": {}}
    bluesky = RecordingSuccessAdapter("bluesky")
    failing_x = FailingAdapter()
    failing_x.name = "x"

    summary, next_state = run_syndication(
        config,
        state,
        feed_client=FakeFeedClient(),
        adapters={"bluesky": bluesky, "x": failing_x},
        archive_dir=str(tmp_path / "archive"),
        delivery_state=delivery_state,
    )

    assert [post["post_id"] for post in bluesky.sent_posts] == ["post-1"]
    assert delivery_state["delivered_post_ids"]["bluesky"]["agency.bsky.social"] == ["post-1"]
    assert "x" not in delivery_state["delivered_post_ids"]
    assert delivery_state["pending_post_ids"]["x"]["agency.bsky.social"] == ["post-1"]
    assert next_state["last_seen_post_ids"]["agency.bsky.social"] == "post-1"
    assert summary.accounts[0].results[-1].platform == "x"
    assert summary.accounts[0].results[-1].success is False


def test_runner_retries_pending_x_from_archive(tmp_path) -> None:
    config = make_config()
    config["monitored_accounts"][0]["syndicate_to"] = ["x"]
    config["syndication_targets"] = {"x": {"enabled": True, "max_posts_per_run": 1}}
    archive_dir = tmp_path / "archive"
    account_dir = archive_dir / "agency.bsky.social"
    account_dir.mkdir(parents=True)
    write_archive_record(account_dir, "post-1")
    state: AppState = {"last_seen_post_ids": {"agency.bsky.social": "post-1"}}
    delivery_state = {
        "delivered_post_ids": {},
        "pending_post_ids": {"x": {"agency.bsky.social": ["post-1"]}},
    }
    x = RecordingSuccessAdapter("x")

    summary, next_state = run_syndication(
        config,
        state,
        feed_client=EmptyFeedClient(),
        adapters={"x": x},
        archive_dir=str(archive_dir),
        delivery_state=delivery_state,
    )

    assert summary.fetched == 0
    assert summary.syndicated == 1
    assert [post["post_id"] for post in x.sent_posts] == ["post-1"]
    assert delivery_state["delivered_post_ids"]["x"]["agency.bsky.social"] == ["post-1"]
    assert delivery_state["pending_post_ids"] == {}
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
