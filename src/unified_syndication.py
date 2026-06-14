from src.bluesky import BlueskyPost
from src.syndication import SyndicationAdapter, SyndicationResult


class UnifiedTransparencyAdapter:
    """Adapter that wraps another adapter to add agency-level attribution for a unified feed."""

    name = "unified"

    def __init__(self, base_adapter: SyndicationAdapter, agency_map: dict[str, str]) -> None:
        self.base_adapter = base_adapter
        self.agency_map = agency_map

    def send(self, post: BlueskyPost) -> SyndicationResult:
        agency_name = self.agency_map.get(post["handle"], post["handle"])
        attributed_post = post.copy()
        attributed_post["text"] = f"[{agency_name}] {post['text']}"
        return self.base_adapter.send(attributed_post)
