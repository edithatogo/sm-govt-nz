from scripts.threads_dry_run_latest import build_latest_threads_payload


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


def test_build_latest_threads_payload_redacts_token_and_keeps_replay_disabled(
    monkeypatch,
    tmp_path,
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        """
{
  "monitored_accounts": [
    {
      "handle": "agency.bsky.social",
      "did": "did:plc:agency",
      "name": "Agency",
      "syndicate_to": ["threads"]
    }
  ],
  "syndication_targets": {
    "threads": {
      "enabled": true,
      "archive_replay_enabled": false,
      "account_handle": "mirnzcourts",
      "profile_url": "https://www.threads.com/@mirnzcourts"
    }
  }
}
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("THREADS_USER_ID", "threads-user")
    monkeypatch.setenv("THREADS_ACCESS_TOKEN", "secret-token")

    payload = build_latest_threads_payload(
        config_path=str(config_path),
        feed_client=FakeFeedClient(),
    )

    create_request = payload["requests"]["create_container"]
    assert create_request["url"] == "https://graph.threads.net/v1.0/threads-user/threads"
    assert create_request["form"]["access_token"] == "<redacted>"
    assert create_request["form"]["media_type"] == "TEXT"
    assert payload["target"]["historical_replay_enabled"] is False
    assert payload["source"]["post_id"] == "post-1"
