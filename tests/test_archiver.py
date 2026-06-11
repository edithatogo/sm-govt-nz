from hypothesis import given, settings, strategies as st
import json
import tempfile

from src.archiver import archive_bluesky_post, archive_post, load_post_archive, write_timeline

def test_archive_new_post(tmp_path):
    archive_dir = str(tmp_path)
    agency = "test-agency"
    post_id = "post-1"
    content = "Hello, world!"
    created_at = "2026-06-10T00:00:00Z"
    media_urls = ["http://example.com/image.jpg"]
    alt_text = "An example image"

    post = archive_post(
        agency=agency,
        post_id=post_id,
        content=content,
        created_at=created_at,
        media_urls=media_urls,
        alt_text=alt_text,
        archive_dir=archive_dir
    )

    assert post["post_id"] == post_id
    assert post["content"] == content
    assert post["edit_history"] == []

    # Reload from disk and check
    reloaded = load_post_archive(agency, post_id, archive_dir)
    assert reloaded is not None
    assert reloaded["content"] == content

def test_archive_edited_post(tmp_path):
    archive_dir = str(tmp_path)
    agency = "test-agency"
    post_id = "post-1"
    created_at = "2026-06-10T00:00:00Z"

    # Save original post
    archive_post(
        agency=agency,
        post_id=post_id,
        content="Original content",
        created_at=created_at,
        media_urls=[],
        archive_dir=archive_dir
    )

    # Save edit
    edited = archive_post(
        agency=agency,
        post_id=post_id,
        content="Edited content",
        created_at=created_at,
        media_urls=[],
        archive_dir=archive_dir
    )

    assert edited["content"] == "Edited content"
    assert len(edited["edit_history"]) == 1
    assert edited["edit_history"][0]["previous_content"] == "Original content"
    assert "timestamp" in edited["edit_history"][0]

@given(content_a=st.text(min_size=1), content_b=st.text(min_size=1))
@settings(deadline=None)
def test_property_archiving(content_a, content_b):
    # Skip matching inputs to focus on edit differences
    if content_a == content_b:
        return

    with tempfile.TemporaryDirectory() as archive_dir:
        archive_post("agency", "post", content_a, "2026-06-10T00:00:00Z", [], archive_dir=archive_dir)
        edited = archive_post("agency", "post", content_b, "2026-06-10T00:00:00Z", [], archive_dir=archive_dir)

        assert edited["content"] == content_b
        assert edited["edit_history"][0]["previous_content"] == content_a


def test_archive_bluesky_post_and_timeline(tmp_path):
    archive_bluesky_post(
        {
            "post_id": "post-2",
            "uri": "at://did:plc:agency/app.bsky.feed.post/post-2",
            "cid": "cid-2",
            "handle": "agency.bsky.social",
            "author_did": "did:plc:agency",
            "text": "Post text",
            "created_at": "2026-06-10T01:00:00Z",
            "url": "https://bsky.app/profile/agency.bsky.social/post/post-2",
            "images": [{"alt": "Alt text", "fullsize": "https://cdn.example/image.jpg", "thumb": ""}],
        },
        archive_dir=tmp_path / "archive",
    )

    timeline = write_timeline(tmp_path / "archive", tmp_path / "timeline.json")
    saved = json.loads((tmp_path / "timeline.json").read_text(encoding="utf-8"))

    assert timeline[0]["source_url"].endswith("/post-2")
    assert saved[0]["images"][0]["alt"] == "Alt text"
