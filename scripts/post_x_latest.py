import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.bluesky import BlueskyApiClient, normalize_feed_item
from src.config import (
    TargetDeliveryState,
    load_config,
    load_target_delivery_state,
    save_target_delivery_state,
)
from src.syndication import BufferCliAdapter, SyndicationAdapter, SyndicationResult, format_post_text


@dataclass(frozen=True)
class XLatestPostResult:
    source_handle: str
    post_id: str
    source_url: str
    dry_run: bool
    skipped: bool
    success: bool
    detail: str


def run_latest_x_post(
    *,
    config_path: str = "config.json",
    delivery_state_path: str = "conductor/target_delivery_state.json",
    dry_run: bool = True,
    feed_client: Any | None = None,
    adapter: SyndicationAdapter | None = None,
) -> XLatestPostResult:
    config = load_config(config_path)
    source = config["monitored_accounts"][0]
    source_handle = source["handle"]
    x_config = config["syndication_targets"].get("x", {})

    if "x" not in source.get("syndicate_to", []):
        raise RuntimeError(f"{source_handle} is not configured to syndicate to X.")
    if not x_config.get("enabled", False):
        raise RuntimeError("X target is not enabled.")
    if x_config.get("archive_replay_enabled", False):
        raise RuntimeError("X historical archive replay must remain disabled.")
    if x_config.get("route") != "buffer":
        raise RuntimeError("X launch route must be Buffer for this track.")

    client = feed_client or BlueskyApiClient()
    raw_feed = client.fetch_author_feed(source["did"] or source_handle, limit=1)
    if not raw_feed:
        raise RuntimeError(f"No source posts returned for {source_handle}.")
    post = normalize_feed_item(raw_feed[0], source_handle)

    delivery_state = load_target_delivery_state(delivery_state_path)
    if _already_delivered(delivery_state, source_handle, post["post_id"]):
        return XLatestPostResult(
            source_handle=source_handle,
            post_id=post["post_id"],
            source_url=post["url"],
            dry_run=dry_run,
            skipped=True,
            success=True,
            detail="duplicate",
        )

    if dry_run:
        return XLatestPostResult(
            source_handle=source_handle,
            post_id=post["post_id"],
            source_url=post["url"],
            dry_run=True,
            skipped=True,
            success=True,
            detail=json.dumps(_buffer_preview(post, x_config), ensure_ascii=False, sort_keys=True),
        )

    live_adapter = adapter or _build_buffer_adapter()
    result = live_adapter.send(post)
    if not result.success:
        return _from_syndication_result(source_handle, post, False, result)

    _mark_delivered(delivery_state, source_handle, post["post_id"])
    save_target_delivery_state(delivery_state, delivery_state_path)
    return _from_syndication_result(source_handle, post, False, result)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Post the latest configured Courts of NZ source item to X via Buffer only."
    )
    parser.add_argument("--config-path", default="config.json")
    parser.add_argument("--delivery-state-path", default="conductor/target_delivery_state.json")
    parser.add_argument(
        "--confirm-live-posting",
        action="store_true",
        help="Actually publish to X via Buffer. Without this flag, only a dry run is emitted.",
    )
    args = parser.parse_args()

    result = run_latest_x_post(
        config_path=args.config_path,
        delivery_state_path=args.delivery_state_path,
        dry_run=not args.confirm_live_posting,
    )
    print(json.dumps(asdict(result), indent=2, ensure_ascii=False, sort_keys=True))


def _build_buffer_adapter() -> BufferCliAdapter:
    channel_id = os.getenv("BUFFER_X_CHANNEL_ID")
    api_key = os.getenv("BUFFER_API_KEY")
    if not channel_id or not api_key:
        raise RuntimeError("Missing BUFFER_API_KEY and BUFFER_X_CHANNEL_ID.")
    return BufferCliAdapter(
        channel_id,
        command=os.getenv("BUFFER_CLI_COMMAND", "buffer"),
    )


def _already_delivered(
    state: TargetDeliveryState,
    source_handle: str,
    post_id: str,
) -> bool:
    return post_id in set(state.get("delivered_post_ids", {}).get("x", {}).get(source_handle, []))


def _mark_delivered(
    state: TargetDeliveryState,
    source_handle: str,
    post_id: str,
) -> None:
    delivered_by_target = state.setdefault("delivered_post_ids", {})
    delivered_by_handle = delivered_by_target.setdefault("x", {})
    delivered_posts = delivered_by_handle.setdefault(source_handle, [])
    if post_id not in delivered_posts:
        delivered_posts.append(post_id)


def _from_syndication_result(
    source_handle: str,
    post: dict[str, Any],
    dry_run: bool,
    result: SyndicationResult,
) -> XLatestPostResult:
    return XLatestPostResult(
        source_handle=source_handle,
        post_id=str(post["post_id"]),
        source_url=str(post["url"]),
        dry_run=dry_run,
        skipped=result.skipped,
        success=result.success,
        detail=result.detail,
    )


def _buffer_preview(post: dict[str, Any], x_config: dict[str, Any]) -> dict[str, Any]:
    return {
        "route": "buffer",
        "queue_behavior": "shareNow",
        "channel_id_secret": "BUFFER_X_CHANNEL_ID",
        "account_handle": x_config.get("account_handle", ""),
        "profile_url": x_config.get("profile_url", ""),
        "text": format_post_text(post, limit=280),
    }


if __name__ == "__main__":
    main()
