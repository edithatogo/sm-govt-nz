import json

from scripts.unified_transparency_dry_run_latest import build_latest_unified_payload


class FakeFeedClient:
    def fetch_author_feed(self, actor: str, *, limit: int = 50):
        assert actor == "did:plc:agency"
        assert limit == 1
        return [
            {
                "post": {
                    "uri": "at://did:plc:agency/app.bsky.feed.post/post-1",
                    "cid": "cid-1",
                    "author": {"did": "did:plc:agency", "handle": "agency.bsky.social"},
                    "record": {"text": "Official update", "createdAt": "2026-06-10T00:00:00Z"},
                    "embed": {"images": []},
                }
            }
        ]


def test_build_latest_unified_payload_keeps_target_disabled_and_prefixes_agency(
    tmp_path,
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "monitored_accounts": [
                    {
                        "handle": "agency.bsky.social",
                        "did": "did:plc:agency",
                        "name": "Mirror: Agency",
                        "syndicate_to": ["unified"],
                    }
                ],
                "syndication_targets": {
                    "unified": {
                        "enabled": False,
                        "base_target": "bluesky",
                        "archive_replay_enabled": False,
                        "gated_by": "launch_review",
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    payload = build_latest_unified_payload(
        config_path=str(config_path),
        feed_client=FakeFeedClient(),
    )

    assert payload["target"]["enabled"] is False
    assert payload["target"]["historical_replay_enabled"] is False
    assert payload["target"]["base_target"] == "bluesky"
    assert payload["preview"]["post"]["text"] == "[Mirror: Agency] Official update"
    assert payload["preview"]["result"]["skipped"] is True
