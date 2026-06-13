import json

from scripts.facebook_dry_run_latest import build_latest_facebook_payload


class FakeFeedClient:
    def fetch_author_feed(self, actor, limit):
        return [
            {
                "post": {
                    "uri": "at://did:plc:agency/app.bsky.feed.post/post-1",
                    "cid": "cid-1",
                    "author": {"did": "did:plc:agency", "handle": "agency.bsky.social"},
                    "record": {
                        "text": "Official update",
                        "createdAt": "2026-06-10T00:00:00Z",
                    },
                    "embed": {},
                }
            }
        ]


def test_build_latest_facebook_payload_redacts_token_and_keeps_disabled(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "monitored_accounts": [
                    {
                        "handle": "agency.bsky.social",
                        "did": "did:plc:agency",
                        "name": "Mirror: Agency",
                        "syndicate_to": ["facebook"],
                    }
                ],
                "syndication_targets": {
                    "facebook": {
                        "enabled": False,
                        "archive_replay_enabled": False,
                        "account_handle": "mirnzcourts",
                        "profile_url": "https://www.facebook.com/mirnzcourts",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("FACEBOOK_PAGE_ID", "page-id")
    monkeypatch.setenv("FACEBOOK_PAGE_ACCESS_TOKEN", "secret")

    payload = build_latest_facebook_payload(
        config_path=str(config_path),
        feed_client=FakeFeedClient(),
    )

    assert payload["target"]["enabled"] is False
    assert payload["target"]["historical_replay_enabled"] is False
    assert payload["request"]["url"] == "https://graph.facebook.com/v20.0/page-id/feed"
    assert payload["request"]["form"]["access_token"] == "<redacted>"
    assert "Original:" in payload["request"]["form"]["message"]
