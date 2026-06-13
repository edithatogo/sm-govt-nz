from scripts.threads_api_probe import probe_threads_profile


class FakeHttpClient:
    def __init__(self) -> None:
        self.urls = []

    def get_json(self, url, headers=None):
        self.urls.append(url)
        return {"id": "threads-user", "username": "mirnzcourts", "name": "Mirror"}


def test_probe_threads_profile_reads_identity_without_posting() -> None:
    client = FakeHttpClient()

    profile = probe_threads_profile(
        user_id="threads-user",
        access_token="token",
        client=client,
    )

    assert profile["username"] == "mirnzcourts"
    assert "/threads-user?" in client.urls[0]
    assert "threads_profile_picture_url" in client.urls[0]
