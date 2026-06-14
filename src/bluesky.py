import json
from typing import Any, Mapping, Protocol, TypedDict
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from src.config import MonitoredAccount


class BlueskyImage(TypedDict):
    alt: str
    fullsize: str
    thumb: str


class BlueskyPost(TypedDict):
    post_id: str
    uri: str
    cid: str
    handle: str
    author_did: str
    text: str
    created_at: str
    url: str
    images: list[BlueskyImage]


class AuthorFeedClient(Protocol):
    def fetch_author_feed(self, actor: str, *, limit: int = 50) -> list[Mapping[str, Any]]:
        """Return raw AT Protocol feed items for an actor."""

    def get_relationships(self, actor: str, others: list[str]) -> list[Mapping[str, Any]]:
        """Return relationship data between an actor and others."""

    def resolve_handle(self, handle: str) -> str:
        """Return the DID for a Bluesky handle."""


class BlueskyApiClient:
    """Small AT Protocol XRPC client for unauthenticated public author feeds."""

    def __init__(
        self,
        base_url: str = "https://public.api.bsky.app",
        timeout_seconds: float = 10.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def fetch_author_feed(self, actor: str, *, limit: int = 50) -> list[Mapping[str, Any]]:
        query = urlencode({"actor": actor, "limit": str(limit)})
        url = f"{self.base_url}/xrpc/app.bsky.feed.getAuthorFeed?{query}"
        request = Request(url, headers={"Accept": "application/json"})

        with urlopen(request, timeout=self.timeout_seconds) as response:
            body = response.read().decode("utf-8")

        payload = json.loads(body)
        feed = payload.get("feed", [])
        if not isinstance(feed, list):
            raise ValueError("Invalid Bluesky response: 'feed' must be a list.")
        return feed

    def get_relationships(self, actor: str, others: list[str]) -> list[Mapping[str, Any]]:
        """Check relationships between actor and others using app.bsky.graph.getRelationships."""
        params = [("actor", actor)]
        for other in others:
            params.append(("others", other))

        query = urlencode(params)
        url = f"{self.base_url}/xrpc/app.bsky.graph.getRelationships?{query}"
        request = Request(url, headers={"Accept": "application/json"})

        with urlopen(request, timeout=self.timeout_seconds) as response:
            body = response.read().decode("utf-8")

        payload = json.loads(body)
        relationships = payload.get("relationships", [])
        if not isinstance(relationships, list):
            raise ValueError("Invalid Bluesky response: 'relationships' must be a list.")
        return relationships

    def resolve_handle(self, handle: str) -> str:
        query = urlencode({"handle": handle})
        url = f"{self.base_url}/xrpc/com.atproto.identity.resolveHandle?{query}"
        request = Request(url, headers={"Accept": "application/json"})

        with urlopen(request, timeout=self.timeout_seconds) as response:
            body = response.read().decode("utf-8")

        payload = json.loads(body)
        did = payload.get("did")
        if not isinstance(did, str) or not did:
            raise ValueError("Invalid Bluesky response: 'did' must be a string.")
        return did


def extract_post_id(uri: str) -> str:
    """Extract the AT Protocol record key from a post URI."""
    if not uri:
        return ""
    return uri.rstrip("/").split("/")[-1]


def build_post_url(handle: str, uri: str) -> str:
    """Build a browser URL for a Bluesky post."""
    post_id = extract_post_id(uri)
    return f"https://bsky.app/profile/{handle}/post/{post_id}"


def normalize_feed_item(
    feed_item: Mapping[str, Any],
    fallback_handle: str,
) -> BlueskyPost:
    """Convert a raw feed item into the local post contract."""
    post = _mapping(feed_item.get("post"))
    author = _mapping(post.get("author"))
    record = _mapping(post.get("record"))
    embed = _mapping(post.get("embed"))

    handle = str(author.get("handle") or fallback_handle)
    uri = str(post.get("uri") or "")

    return {
        "post_id": extract_post_id(uri),
        "uri": uri,
        "cid": str(post.get("cid") or ""),
        "handle": handle,
        "author_did": str(author.get("did") or ""),
        "text": str(record.get("text") or ""),
        "created_at": str(record.get("createdAt") or ""),
        "url": build_post_url(handle, uri),
        "images": _extract_images(embed),
    }


def fetch_new_posts_for_account(
    account: MonitoredAccount,
    last_seen_post_id: str = "",
    *,
    client: AuthorFeedClient | None = None,
    limit: int = 50,
) -> list[BlueskyPost]:
    """Fetch posts newer than the last processed record key for an account.

    Bluesky author feeds are returned newest-first. This function stops at the
    first matching `last_seen_post_id` and returns posts oldest-first so callers
    can syndicate them in natural order.
    """
    feed_client = client or BlueskyApiClient()
    actor = account["did"] or account["handle"]
    raw_items = feed_client.fetch_author_feed(actor, limit=limit)

    new_posts: list[BlueskyPost] = []
    for item in raw_items:
        post = normalize_feed_item(item, account["handle"])
        if post["post_id"] == last_seen_post_id:
            break
        if post["post_id"]:
            new_posts.append(post)

    return list(reversed(new_posts))


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _extract_images(embed: Mapping[str, Any]) -> list[BlueskyImage]:
    raw_images = embed.get("images", [])
    if not isinstance(raw_images, list):
        return []

    images: list[BlueskyImage] = []
    for image in raw_images:
        image_data = _mapping(image)
        images.append(
            {
                "alt": str(image_data.get("alt") or ""),
                "fullsize": str(image_data.get("fullsize") or ""),
                "thumb": str(image_data.get("thumb") or ""),
            }
        )
    return images
