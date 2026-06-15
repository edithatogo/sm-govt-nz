from scripts.instagram_api_probe import (
    INSTAGRAM_PROFILE_FIELDS,
    probe_instagram_profile,
    safe_profile_summary,
)
from urllib.parse import urlencode


class FakeHttpClient:
    def __init__(self) -> None:
        self.urls = []

    def get_json(self, url, headers=None):
        self.urls.append(url)
        return {
            "id": "ig-user",
            "username": "mirnzcourts",
            "account_type": "BUSINESS",
            "media_count": 42,
            "name": "Mirror: Courts of New Zealand",
            "is_business": True,
        }


class TestProbeInstagramProfile:
    def test_reads_identity_without_posting(self) -> None:
        client = FakeHttpClient()

        profile = probe_instagram_profile(
            user_id="ig-user",
            access_token="token",
            client=client,
        )

        assert profile["username"] == "mirnzcourts"
        assert "/ig-user?" in client.urls[0]
        expected_fields = urlencode({"fields": INSTAGRAM_PROFILE_FIELDS, "access_token": "token"})
        assert client.urls[0].endswith(expected_fields)

    def test_returns_extra_fields_for_readiness_check(self) -> None:
        client = FakeHttpClient()

        profile = probe_instagram_profile(
            user_id="ig-user",
            access_token="token",
            client=client,
        )

        assert profile.get("account_type") == "BUSINESS"
        assert profile.get("media_count") == 42
        assert profile.get("is_business") is True


class TestSafeProfileSummary:
    def test_extracts_safe_fields_without_token(self) -> None:
        raw = {
            "id": "ig-user",
            "username": "mirnzcourts",
            "account_type": "CREATOR",
            "media_count": 10,
        }
        safe = safe_profile_summary(raw)
        assert safe["id"] == "ig-user"
        assert safe["username"] == "mirnzcourts"
        assert safe["account_type"] == "CREATOR"
        assert safe["media_count"] == 10
        # Token should never appear in the safe output
        assert "access_token" not in safe

    def test_handles_missing_fields_gracefully(self) -> None:
        safe = safe_profile_summary({})
        assert safe["id"] is None
        assert safe["account_type"] is None
