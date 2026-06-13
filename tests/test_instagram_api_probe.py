from scripts.instagram_api_probe import probe_instagram_profile


class FakeHttpClient:
    def __init__(self) -> None:
        self.urls = []

    def get_json(self, url, headers=None):
        self.urls.append(url)
        return {"id": "ig-user", "username": "mirnzcourts"}


def test_probe_instagram_profile_reads_identity_without_posting() -> None:
    client = FakeHttpClient()

    profile = probe_instagram_profile(
        user_id="ig-user",
        access_token="token",
        client=client,
    )

    assert profile["username"] == "mirnzcourts"
    assert "/ig-user?" in client.urls[0]
    assert "fields=id%2Cusername" in client.urls[0]
