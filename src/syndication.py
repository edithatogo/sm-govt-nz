import json
import os
import subprocess
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from src.bluesky import BlueskyPost


class SyndicationAdapter(Protocol):
    name: str

    def send(self, post: BlueskyPost) -> "SyndicationResult":
        """Syndicate a normalized Bluesky post."""


@dataclass(frozen=True)
class SyndicationResult:
    platform: str
    success: bool
    skipped: bool = False
    detail: str = ""


class DryRunAdapter:
    def __init__(self, name: str) -> None:
        self.name = name
        self.sent_posts: list[BlueskyPost] = []

    def send(self, post: BlueskyPost) -> SyndicationResult:
        self.sent_posts.append(post)
        return SyndicationResult(self.name, success=True, skipped=True, detail="dry-run")


class JsonHttpClient:
    def get_json(
        self,
        url: str,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        request = Request(url, headers={"Accept": "application/json", **(headers or {})})
        with urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8")
        if not body:
            return {}
        return json.loads(body)

    def post_json(
        self,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        request_headers = {"Content-Type": "application/json", **(headers or {})}
        request = Request(url, data=data, headers=request_headers, method="POST")
        with urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8")
        if not body:
            return {}
        return json.loads(body)

    def post_form(
        self,
        url: str,
        payload: dict[str, str],
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        data = urlencode(payload).encode("utf-8")
        request_headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            **(headers or {}),
        }
        request = Request(url, data=data, headers=request_headers, method="POST")
        with urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8")
        if not body:
            return {}
        return json.loads(body)


class DiscordWebhookAdapter:
    name = "discord"

    def __init__(self, webhook_url: str, client: JsonHttpClient | None = None) -> None:
        self.webhook_url = webhook_url
        self.client = client or JsonHttpClient()

    def send(self, post: BlueskyPost) -> SyndicationResult:
        payload = {
            "content": format_post_text(post, limit=1900),
            "embeds": [
                {
                    "title": f"Bluesky post from {post['handle']}",
                    "url": post["url"],
                    "description": post["text"],
                }
            ],
        }
        self.client.post_json(self.webhook_url, payload)
        return SyndicationResult(self.name, success=True)


class MastodonAdapter:
    name = "mastodon"

    def __init__(
        self,
        base_url: str,
        access_token: str,
        client: JsonHttpClient | None = None,
        visibility: str = "public",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.access_token = access_token
        self.client = client or JsonHttpClient()
        self.visibility = visibility

    def send(self, post: BlueskyPost) -> SyndicationResult:
        payload = {
            "status": format_post_text(post, limit=500),
            "visibility": self.visibility,
        }
        headers = {"Authorization": f"Bearer {self.access_token}"}
        self.client.post_form(f"{self.base_url}/api/v1/statuses", payload, headers)
        return SyndicationResult(self.name, success=True)


class GenericApiAdapter:
    def __init__(
        self,
        name: str,
        endpoint_url: str,
        bearer_token: str,
        limit: int,
        client: JsonHttpClient | None = None,
    ) -> None:
        self.name = name
        self.endpoint_url = endpoint_url
        self.bearer_token = bearer_token
        self.limit = limit
        self.client = client or JsonHttpClient()

    def send(self, post: BlueskyPost) -> SyndicationResult:
        payload = {
            "text": format_post_text(post, limit=self.limit),
            "source_url": post["url"],
            "images": post["images"],
        }
        headers = {"Authorization": f"Bearer {self.bearer_token}"}
        self.client.post_json(self.endpoint_url, payload, headers)
        return SyndicationResult(self.name, success=True)


class ThreadsApiAdapter:
    """Outbound adapter for Meta's official Threads API publish flow."""

    name = "threads"

    def __init__(
        self,
        user_id: str,
        access_token: str,
        *,
        api_base_url: str = "https://graph.threads.net/v1.0",
        client: JsonHttpClient | None = None,
        text_limit: int = 500,
    ) -> None:
        self.user_id = user_id
        self.access_token = access_token
        self.api_base_url = api_base_url.rstrip("/")
        self.client = client or JsonHttpClient()
        self.text_limit = text_limit

    def send(self, post: BlueskyPost) -> SyndicationResult:
        container_payload = self.container_payload(post)
        container = self.client.post_form(
            f"{self.api_base_url}/{self.user_id}/threads",
            container_payload,
        )
        creation_id = str(container.get("id", ""))
        if not creation_id:
            return SyndicationResult(self.name, success=False, detail="missing creation id")

        published = self.client.post_form(
            f"{self.api_base_url}/{self.user_id}/threads_publish",
            {
                "creation_id": creation_id,
                "access_token": self.access_token,
            },
        )
        return SyndicationResult(
            self.name,
            success=True,
            detail=str(published.get("id", "")),
        )

    def container_payload(self, post: BlueskyPost) -> dict[str, str]:
        text = format_post_text(post, limit=self.text_limit)
        payload = {
            "media_type": "TEXT",
            "text": text,
            "access_token": self.access_token,
        }
        image_url = _first_image_url(post)
        if image_url:
            payload["media_type"] = "IMAGE"
            payload["image_url"] = image_url
        return payload


class FacebookPageAdapter:
    """Outbound adapter for Meta's official Facebook Page publishing flow."""

    name = "facebook"

    def __init__(
        self,
        page_id: str,
        page_access_token: str,
        *,
        api_base_url: str = "https://graph.facebook.com/v20.0",
        client: JsonHttpClient | None = None,
        text_limit: int = 63206,
    ) -> None:
        self.page_id = page_id
        self.page_access_token = page_access_token
        self.api_base_url = api_base_url.rstrip("/")
        self.client = client or JsonHttpClient()
        self.text_limit = text_limit

    def send(self, post: BlueskyPost) -> SyndicationResult:
        endpoint, payload = self.publish_request(post)
        published = self.client.post_form(endpoint, payload)
        return SyndicationResult(
            self.name,
            success=True,
            detail=str(published.get("id", "") or published.get("post_id", "")),
        )

    def publish_request(self, post: BlueskyPost) -> tuple[str, dict[str, str]]:
        message = format_post_text(post, limit=self.text_limit)
        image_url = _first_image_url(post)
        if image_url:
            return (
                f"{self.api_base_url}/{self.page_id}/photos",
                {
                    "url": image_url,
                    "caption": message,
                    "access_token": self.page_access_token,
                },
            )
        return (
            f"{self.api_base_url}/{self.page_id}/feed",
            {
                "message": message,
                "access_token": self.page_access_token,
            },
        )


class ZernioCliAdapter:
    """Outbound adapter backed by zernio-cli connected social accounts."""

    def __init__(
        self,
        name: str,
        account_ids: list[str],
        *,
        command: str = "zernio",
        text_limit: int = 3000,
    ) -> None:
        self.name = name
        self.account_ids = account_ids
        self.command = command
        self.text_limit = text_limit

    def send(self, post: BlueskyPost) -> SyndicationResult:
        args = [
            self.command,
            "posts:create",
            "--text",
            format_post_text(post, limit=self.text_limit),
            "--accounts",
            ",".join(self.account_ids),
        ]
        media_urls = [image["fullsize"] for image in post["images"] if image.get("fullsize")]
        if media_urls:
            args.extend(["--media", ",".join(media_urls)])

        completed = subprocess.run(args, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            return SyndicationResult(
                self.name,
                success=False,
                detail=(completed.stderr or completed.stdout).strip(),
            )
        return SyndicationResult(self.name, success=True, detail=completed.stdout.strip())


class BufferCliAdapter:
    """Outbound adapter backed by Buffer's official CLI."""

    def __init__(
        self,
        channel_id: str,
        *,
        command: str = "buffer",
        text_limit: int = 280,
    ) -> None:
        self.name = "x"
        self.channel_id = channel_id
        self.command = command
        self.text_limit = text_limit

    def send(self, post: BlueskyPost) -> SyndicationResult:
        args = [
            self.command,
            "posts",
            "create",
            "--scheduling-type",
            "automatic",
            "--mode",
            "shareNow",
            "--channel-id",
            self.channel_id,
            "--text",
            format_post_text(post, limit=self.text_limit),
            "--source",
            "sm-govt-nz",
            "--output",
            "json",
            "--quiet",
        ]

        completed = subprocess.run(args, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            return SyndicationResult(
                self.name,
                success=False,
                detail=(completed.stderr or completed.stdout).strip(),
            )
        return SyndicationResult(self.name, success=True, detail=completed.stdout.strip())


class TweepyXAdapter:
    name = "x"

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        access_token: str,
        access_token_secret: str,
        *,
        client: Any | None = None,
    ) -> None:
        self.client = client or _build_tweepy_client(
            api_key,
            api_secret,
            access_token,
            access_token_secret,
        )

    def send(self, post: BlueskyPost) -> SyndicationResult:
        response = self.client.create_tweet(text=format_post_text(post, limit=280))
        tweet_id = _tweet_id_from_response(response)
        return SyndicationResult(self.name, success=True, detail=tweet_id)


class BlueskyMirrorAdapter:
    """Outbound adapter for a dedicated Bluesky mirror account."""

    name = "bluesky"

    def __init__(
        self,
        handle: str,
        app_password: str,
        *,
        client: Any | None = None,
        text_limit: int = 300,
    ) -> None:
        self.handle = handle
        self.app_password = app_password
        self.client = client or _build_atproto_client()
        self.text_limit = text_limit
        self._logged_in = False

    def send(self, post: BlueskyPost) -> SyndicationResult:
        if not self._logged_in:
            self.client.login(self.handle, self.app_password)
            self._logged_in = True
        response = self.client.send_post(format_post_text(post, limit=self.text_limit))
        return SyndicationResult(
            self.name,
            success=True,
            detail=_atproto_post_uri_from_response(response),
        )


def format_post_text(post: BlueskyPost, *, limit: int) -> str:
    suffix = f"\n\nOriginal: {post['url']}"
    text = post["text"].strip()
    if len(text) + len(suffix) <= limit:
        return f"{text}{suffix}" if text else post["url"]

    room = max(0, limit - len(suffix) - 1)
    trimmed = text[:room].rstrip()
    return f"{trimmed}…{suffix}"


def build_adapters_from_env(targets: list[str]) -> dict[str, SyndicationAdapter]:
    adapters: dict[str, SyndicationAdapter] = {}
    for target in targets:
        adapter = _build_adapter_from_env(target)
        if adapter is not None:
            adapters[target] = adapter
    return adapters


def _build_adapter_from_env(target: str) -> SyndicationAdapter | None:
    if target == "discord":
        webhook = os.getenv("DISCORD_WEBHOOK_URL")
        return DiscordWebhookAdapter(webhook) if webhook else None
    if target == "mastodon":
        base_url = os.getenv("MASTODON_BASE_URL")
        token = os.getenv("MASTODON_ACCESS_TOKEN")
        if base_url and token:
            return MastodonAdapter(base_url, token)
        return None
    if target == "x":
        buffer_channel_id = os.getenv("BUFFER_X_CHANNEL_ID")
        if buffer_channel_id and os.getenv("BUFFER_API_KEY"):
            return BufferCliAdapter(
                buffer_channel_id,
                command=os.getenv("BUFFER_CLI_COMMAND", "buffer"),
            )
        api_key = os.getenv("X_API_KEY")
        api_secret = os.getenv("X_API_SECRET")
        access_token = os.getenv("X_ACCESS_TOKEN")
        access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")
        if api_key and api_secret and access_token and access_token_secret:
            return TweepyXAdapter(api_key, api_secret, access_token, access_token_secret)
        return None
    if target == "threads":
        user_id = os.getenv("THREADS_USER_ID") or os.getenv("THREADS_MIRROR_ACCOUNT_ID")
        token = os.getenv("THREADS_ACCESS_TOKEN")
        if user_id and token:
            return ThreadsApiAdapter(
                user_id,
                token,
                api_base_url=os.getenv("THREADS_API_BASE_URL", "https://graph.threads.net/v1.0"),
            )
        return None
    if target == "facebook":
        page_id = os.getenv("FACEBOOK_PAGE_ID")
        token = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
        if page_id and token:
            return FacebookPageAdapter(
                page_id,
                token,
                api_base_url=os.getenv("FACEBOOK_API_BASE_URL", "https://graph.facebook.com/v20.0"),
            )
        return None
    if target == "bluesky":
        handle = os.getenv("BLUESKY_MIRROR_HANDLE")
        app_password = os.getenv("BLUESKY_MIRROR_APP_PASSWORD")
        if handle and app_password:
            return BlueskyMirrorAdapter(handle, app_password)
        return None
    if target == "linkedin":
        endpoint = os.getenv("LINKEDIN_API_ENDPOINT")
        token = os.getenv("LINKEDIN_ACCESS_TOKEN")
        if endpoint and token:
            return GenericApiAdapter("linkedin", endpoint, token, limit=3000)
        return None
    return None


def _platform_limit(target: str) -> int:
    return {
        "x": 280,
        "mastodon": 500,
        "threads": 500,
        "facebook": 63206,
        "linkedin": 3000,
        "discord": 1900,
        "bluesky": 300,
    }.get(target, 3000)


def _build_tweepy_client(
    api_key: str,
    api_secret: str,
    access_token: str,
    access_token_secret: str,
) -> Any:
    try:
        import tweepy
    except ImportError as error:
        raise RuntimeError("Install tweepy to use direct X posting.") from error
    return tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_token_secret,
    )


def _build_atproto_client() -> Any:
    try:
        from atproto import Client
    except ImportError as error:
        raise RuntimeError("Install atproto to use Bluesky mirror posting.") from error
    return Client()


def _tweet_id_from_response(response: Any) -> str:
    data = getattr(response, "data", None)
    if isinstance(data, dict):
        return str(data.get("id", ""))
    if isinstance(response, dict):
        response_data = response.get("data", {})
        if isinstance(response_data, dict):
            return str(response_data.get("id", ""))
    return ""


def _atproto_post_uri_from_response(response: Any) -> str:
    uri = getattr(response, "uri", None)
    if uri:
        return str(uri)
    if isinstance(response, dict):
        return str(response.get("uri", ""))
    return ""


def _first_image_url(post: BlueskyPost) -> str:
    for image in post["images"]:
        fullsize = image.get("fullsize")
        if fullsize:
            return str(fullsize)
    return ""
