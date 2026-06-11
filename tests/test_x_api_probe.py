from scripts.x_api_probe import run_probe


def test_run_probe_reports_missing_credentials(monkeypatch) -> None:
    for name in ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"]:
        monkeypatch.delenv(name, raising=False)

    result = run_probe()

    assert result["valid"] is False
    assert result["missing"] == ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"]


def test_run_probe_validates_identity_without_write_probe(monkeypatch) -> None:
    _set_env(monkeypatch)
    monkeypatch.setattr("scripts.x_api_probe.tweepy.Client", FakeClient)

    result = run_probe()

    assert result["valid"] is True
    assert result["identity"]["username"] == "MirNZCourts"
    assert result["write_probe"] is None


def test_run_probe_can_create_and_delete_probe_post(monkeypatch) -> None:
    _set_env(monkeypatch)
    monkeypatch.setattr("scripts.x_api_probe.tweepy.Client", FakeClient)

    result = run_probe(write_probe=True)

    assert result["valid"] is True
    assert result["write_probe"]["ok"] is True
    assert result["write_probe"]["tweet_id"] == "tweet-1"
    assert result["write_probe"]["deleted"] is True


def _set_env(monkeypatch) -> None:
    monkeypatch.setenv("X_API_KEY", "key")
    monkeypatch.setenv("X_API_SECRET", "secret")
    monkeypatch.setenv("X_ACCESS_TOKEN", "token")
    monkeypatch.setenv("X_ACCESS_TOKEN_SECRET", "token-secret")


class FakeUser:
    id = "2064699394176557056"
    username = "MirNZCourts"
    name = "Mirror: Courts of New Zealand"


class FakeResponse:
    def __init__(self, data) -> None:
        self.data = data


class FakeClient:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs

    def get_me(self, user_auth: bool):
        assert user_auth is True
        return FakeResponse(FakeUser())

    def create_tweet(self, text: str):
        assert "Courts mirror API write probe" in text
        return FakeResponse({"id": "tweet-1"})

    def delete_tweet(self, tweet_id: str):
        assert tweet_id == "tweet-1"
        return FakeResponse({"deleted": True})
