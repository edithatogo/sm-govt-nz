from scripts.facebook_page_probe import probe_facebook_page, safe_page_profile


class FakeHttpClient:
    def __init__(self) -> None:
        self.urls = []

    def get_json(self, url, headers=None):
        self.urls.append(url)
        return {
            "id": "page-id",
            "name": "Mirror: Courts of New Zealand",
            "link": "https://www.facebook.com/mirnzcourts",
            "tasks": ["CREATE_CONTENT", "MODERATE"],
            "access_token": "page-token",
        }


def test_probe_facebook_page_reads_identity_without_posting() -> None:
    client = FakeHttpClient()

    profile = probe_facebook_page(
        page_id="page-id",
        page_access_token="token",
        client=client,
    )

    assert profile["name"] == "Mirror: Courts of New Zealand"
    assert "/page-id?" in client.urls[0]
    assert "fields=id%2Cname%2Clink%2Ctasks%2Caccess_token" in client.urls[0]


def test_safe_page_profile_redacts_token_presence() -> None:
    safe = safe_page_profile(
        {
            "id": "page-id",
            "name": "Mirror: Courts of New Zealand",
            "link": "https://www.facebook.com/mirnzcourts",
            "tasks": ["CREATE_CONTENT"],
            "access_token": "secret",
        }
    )

    assert safe == {
        "id": "page-id",
        "name": "Mirror: Courts of New Zealand",
        "link": "https://www.facebook.com/mirnzcourts",
        "tasks": ["CREATE_CONTENT"],
        "has_page_access_token": True,
    }
