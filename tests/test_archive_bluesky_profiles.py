from scripts.archive_bluesky_profiles import extension_from_url, safe_name


def test_safe_name_normalizes_profile_handle() -> None:
    assert safe_name("MirNZCourts.bsky.social") == "mirnzcourts-bsky-social"


def test_extension_from_url_defaults_when_missing() -> None:
    assert extension_from_url("https://cdn.example/avatar") == ".bin"
    assert extension_from_url("https://cdn.example/banner.jpg?token=1") == ".jpg"
