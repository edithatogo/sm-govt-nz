from src.bluesky import BlueskyPost
from src.syndication import (
    DiscordWebhookAdapter,
    DryRunAdapter,
    MastodonAdapter,
    TweepyXAdapter,
    ZernioCliAdapter,
    build_adapters_from_env,
    format_post_text,
)


class FakeHttpClient:
    def __init__(self) -> None:
        self.json_calls = []
        self.form_calls = []

    def post_json(self, url, payload, headers=None):
        self.json_calls.append((url, payload, headers or {}))
        return {"ok": True}

    def post_form(self, url, payload, headers=None):
        self.form_calls.append((url, payload, headers or {}))
        return {"id": "remote-1"}


def test_format_post_text_appends_original_url_and_truncates() -> None:
    post = make_post(text="A" * 320)

    formatted = format_post_text(post, limit=280)

    assert len(formatted) <= 280
    assert "Original: https://bsky.app/profile/agency/post/post-1" in formatted
    assert "…" in formatted


def test_discord_adapter_posts_webhook_payload() -> None:
    client = FakeHttpClient()
    adapter = DiscordWebhookAdapter("https://discord.example/webhook", client)

    result = adapter.send(make_post())

    assert result.success is True
    assert client.json_calls[0][0] == "https://discord.example/webhook"
    assert client.json_calls[0][1]["embeds"][0]["url"].endswith("/post-1")


def test_mastodon_adapter_posts_status_with_bearer_token() -> None:
    client = FakeHttpClient()
    adapter = MastodonAdapter("https://mastodon.example", "token-1", client)

    result = adapter.send(make_post())

    assert result.success is True
    url, payload, headers = client.form_calls[0]
    assert url == "https://mastodon.example/api/v1/statuses"
    assert payload["visibility"] == "public"
    assert headers["Authorization"] == "Bearer token-1"


def test_dry_run_adapter_records_without_remote_post() -> None:
    adapter = DryRunAdapter("x")
    post = make_post()

    result = adapter.send(post)

    assert result.skipped is True
    assert adapter.sent_posts == [post]


def test_zernio_adapter_invokes_posts_create(monkeypatch) -> None:
    calls = []

    def fake_run(args, capture_output, text, check):
        calls.append((args, capture_output, text, check))

        class Completed:
            returncode = 0
            stdout = '{"id":"post-1"}'
            stderr = ""

        return Completed()

    monkeypatch.setattr("src.syndication.subprocess.run", fake_run)

    result = ZernioCliAdapter("linkedin", ["acct-1"], command="zernio-test").send(make_post())

    assert result.success is True
    args = calls[0][0]
    assert args[:2] == ["zernio-test", "posts:create"]
    assert args[args.index("--accounts") + 1] == "acct-1"
    assert "--media" in args


def test_build_adapters_does_not_select_archived_zernio_mapping(monkeypatch) -> None:
    monkeypatch.setenv("ZERNIO_ACCOUNT_IDS_JSON", '{"x":["acct-x"],"linkedin":"acct-link"}')
    monkeypatch.setenv("X_API_KEY", "key")
    monkeypatch.setenv("X_API_SECRET", "secret")
    monkeypatch.setenv("X_ACCESS_TOKEN", "token")
    monkeypatch.setenv("X_ACCESS_TOKEN_SECRET", "token-secret")

    class FakeClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    monkeypatch.setattr("src.syndication._build_tweepy_client", lambda *args: FakeClient(args=args))

    adapters = build_adapters_from_env(["x", "linkedin"])

    assert isinstance(adapters["x"], TweepyXAdapter)
    assert "linkedin" not in adapters


def test_tweepy_x_adapter_posts_with_create_tweet() -> None:
    class FakeTweepyClient:
        def __init__(self) -> None:
            self.text = ""

        def create_tweet(self, text):
            self.text = text
            return {"data": {"id": "tweet-1"}}

    client = FakeTweepyClient()

    result = TweepyXAdapter("key", "secret", "token", "token-secret", client=client).send(make_post())

    assert result.success is True
    assert result.detail == "tweet-1"
    assert "Original:" in client.text


def test_build_adapters_uses_tweepy_for_x_without_zernio(monkeypatch) -> None:
    monkeypatch.delenv("ZERNIO_ACCOUNT_IDS_JSON", raising=False)
    monkeypatch.setenv("X_API_KEY", "key")
    monkeypatch.setenv("X_API_SECRET", "secret")
    monkeypatch.setenv("X_ACCESS_TOKEN", "token")
    monkeypatch.setenv("X_ACCESS_TOKEN_SECRET", "token-secret")

    class FakeClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    monkeypatch.setattr("src.syndication._build_tweepy_client", lambda *args: FakeClient(args=args))

    adapters = build_adapters_from_env(["x"])

    assert isinstance(adapters["x"], TweepyXAdapter)


def make_post(text: str = "Official update") -> BlueskyPost:
    return {
        "post_id": "post-1",
        "uri": "at://did:plc:agency/app.bsky.feed.post/post-1",
        "cid": "cid-1",
        "handle": "agency.bsky.social",
        "author_did": "did:plc:agency",
        "text": text,
        "created_at": "2026-06-10T00:00:00Z",
        "url": "https://bsky.app/profile/agency/post/post-1",
        "images": [
            {
                "alt": "image alt",
                "fullsize": "https://cdn.example/full.jpg",
                "thumb": "https://cdn.example/thumb.jpg",
            }
        ],
    }
