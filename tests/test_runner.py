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
