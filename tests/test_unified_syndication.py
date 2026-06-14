from src.syndication import SyndicationResult
from src.unified_syndication import UnifiedTransparencyAdapter


class RecordingAdapter:
    name = "base"

    def __init__(self) -> None:
        self.sent_posts = []

    def send(self, post):
        self.sent_posts.append(post)
        return SyndicationResult(self.name, success=True, detail=post["text"])


def test_unified_transparency_adapter_prefixes_known_agency_name() -> None:
    base = RecordingAdapter()
    adapter = UnifiedTransparencyAdapter(
        base,
        {"courtsofnz.bsky.social": "Courts of New Zealand"},
    )
    post = make_post("courtsofnz.bsky.social", "Judgment released")

    result = adapter.send(post)

    assert result.success is True
    assert base.sent_posts[0]["text"] == "[Courts of New Zealand] Judgment released"
    assert post["text"] == "Judgment released"


def test_unified_transparency_adapter_falls_back_to_handle() -> None:
    base = RecordingAdapter()
    adapter = UnifiedTransparencyAdapter(base, {})

    adapter.send(make_post("agency.bsky.social", "Public update"))

    assert base.sent_posts[0]["text"] == "[agency.bsky.social] Public update"


def make_post(handle: str, text: str):
    return {
        "post_id": "post-1",
        "uri": "at://did:plc:agency/app.bsky.feed.post/post-1",
        "cid": "cid-1",
        "handle": handle,
        "author_did": "did:plc:agency",
        "text": text,
        "created_at": "2026-06-10T00:00:00Z",
        "url": f"https://bsky.app/profile/{handle}/post/post-1",
        "images": [],
    }
