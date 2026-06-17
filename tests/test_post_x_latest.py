import json
from typing import Any, Mapping

from scripts.post_x_latest import run_latest_x_post
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


class RecordingXAdapter:
    name = "x"

    def __init__(self) -> None:
        self.sent_posts = []

    def send(self, post):
        self.sent_posts.append(post)
        return SyndicationResult("x", success=True, detail='{"post":{"id":"buffer-post-1"}}')


def test_x_dry_run_does_not_mark_delivery(tmp_path) -> None:
    config_path, delivery_path = write_x_files(tmp_path)

    result = run_latest_x_post(
        config_path=str(config_path),
        delivery_state_path=str(delivery_path),
        dry_run=True,
        feed_client=FakeFeedClient(),
    )

    preview = json.loads(result.detail)
    assert result.dry_run is True
    assert result.skipped is True
    assert preview["route"] == "buffer"
    assert preview["queue_behavior"] == "shareNow"
    assert "Original:" in preview["text"]
    assert json.loads(delivery_path.read_text(encoding="utf-8")) == {"delivered_post_ids": {}}


def test_x_live_run_marks_delivery(tmp_path) -> None:
    config_path, delivery_path = write_x_files(tmp_path)
    adapter = RecordingXAdapter()

    result = run_latest_x_post(
        config_path=str(config_path),
        delivery_state_path=str(delivery_path),
        dry_run=False,
        feed_client=FakeFeedClient(),
        adapter=adapter,
    )

    state = json.loads(delivery_path.read_text(encoding="utf-8"))
    assert result.success is True
    assert [post["post_id"] for post in adapter.sent_posts] == ["post-1"]
    assert state["delivered_post_ids"]["x"]["agency.bsky.social"] == ["post-1"]


def test_x_live_run_skips_duplicate(tmp_path) -> None:
    config_path, delivery_path = write_x_files(tmp_path)
    delivery_path.write_text(
        '{"delivered_post_ids": {"x": {"agency.bsky.social": ["post-1"]}}}',
        encoding="utf-8",
    )

    result = run_latest_x_post(
        config_path=str(config_path),
        delivery_state_path=str(delivery_path),
        dry_run=False,
        feed_client=FakeFeedClient(),
        adapter=RecordingXAdapter(),
    )

    assert result.success is True
    assert result.skipped is True
    assert result.detail == "duplicate"


def test_x_rejects_direct_api_route_for_this_track(tmp_path) -> None:
    config_path, delivery_path = write_x_files(tmp_path)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["syndication_targets"]["x"]["route"] = "direct_api"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    try:
        run_latest_x_post(
            config_path=str(config_path),
            delivery_state_path=str(delivery_path),
            dry_run=True,
            feed_client=FakeFeedClient(),
        )
    except RuntimeError as error:
        assert "must be Buffer" in str(error)
    else:
        raise AssertionError("Expected direct API route to be rejected")


def write_x_files(tmp_path):
    config_path = tmp_path / "config.json"
    delivery_path = tmp_path / "target_delivery_state.json"
    config_path.write_text(
        json.dumps(
            {
                "monitored_accounts": [
                    {
                        "handle": "agency.bsky.social",
                        "did": "did:plc:agency",
                        "name": "Agency",
                        "syndicate_to": ["x"],
                    }
                ],
                "syndication_targets": {
                    "x": {
                        "enabled": True,
                        "route": "buffer",
                        "max_posts_per_run": 1,
                        "archive_replay_enabled": False,
                        "account_handle": "MirNZCourts",
                        "profile_url": "https://x.com/MirNZCourts",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    delivery_path.write_text('{"delivered_post_ids": {}}', encoding="utf-8")
    return config_path, delivery_path
