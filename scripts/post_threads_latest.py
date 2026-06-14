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
    load_backlog_state,
    load_config,
    load_target_delivery_state,
    save_target_delivery_state,
)
from src.syndication import SyndicationAdapter, SyndicationResult, ThreadsApiAdapter
from src.threads_pipeline import get_threads_pipeline_status


@dataclass(frozen=True)
class ThreadsLatestPostResult:
    source_handle: str
    post_id: str
    source_url: str
    dry_run: bool
    skipped: bool
    success: bool
    detail: str


def run_latest_threads_post(
    *,
    config_path: str = "config.json",
    delivery_state_path: str = "conductor/target_delivery_state.json",
    backlog_state_path: str = "conductor/bluesky_backlog_state.json",
    archive_dir: str = "historical_archive",
    dry_run: bool = True,
    feed_client: Any | None = None,
    adapter: SyndicationAdapter | None = None,
) -> ThreadsLatestPostResult:
    config = load_config(config_path)
    source = config["monitored_accounts"][0]
    source_handle = source["handle"]
    threads_config = config["syndication_targets"].get("threads", {})

    if "threads" not in source.get("syndicate_to", []):
        raise RuntimeError(f"{source_handle} is not configured to syndicate to Threads.")
    if not threads_config.get("enabled", False):
        raise RuntimeError("Threads target is not enabled.")
    if threads_config.get("archive_replay_enabled", False):
        raise RuntimeError("Threads historical archive replay must remain disabled.")

    backlog_state = load_backlog_state(backlog_state_path)
    status = get_threads_pipeline_status(
        config,
        backlog_state,
        archive_dir=archive_dir,
        source_handle=source_handle,
    )
    if not status.ready_for_threads_posting:
        raise RuntimeError(status.message)

    client = feed_client or BlueskyApiClient()
    raw_feed = client.fetch_author_feed(source["did"] or source_handle, limit=1)
    if not raw_feed:
        raise RuntimeError(f"No source posts returned for {source_handle}.")
    post = normalize_feed_item(raw_feed[0], source_handle)

    delivery_state = load_target_delivery_state(delivery_state_path)
    if _already_delivered(delivery_state, source_handle, post["post_id"]):
        return ThreadsLatestPostResult(
            source_handle=source_handle,
            post_id=post["post_id"],
            source_url=post["url"],
            dry_run=dry_run,
            skipped=True,
            success=True,
            detail="duplicate",
        )

    if dry_run:
        preview_adapter = adapter or _build_threads_adapter()
        detail = ""
        if isinstance(preview_adapter, ThreadsApiAdapter):
            payload = preview_adapter.container_payload(post)
            detail = json.dumps(_redact(payload), ensure_ascii=False, sort_keys=True)
        return ThreadsLatestPostResult(
            source_handle=source_handle,
            post_id=post["post_id"],
            source_url=post["url"],
            dry_run=True,
            skipped=True,
            success=True,
            detail=detail or "dry-run",
        )

    live_adapter = adapter or _build_threads_adapter()
    result = live_adapter.send(post)
    if not result.success:
        return _from_syndication_result(source_handle, post, False, result)

    _mark_delivered(delivery_state, source_handle, post["post_id"])
    save_target_delivery_state(delivery_state, delivery_state_path)
    return _from_syndication_result(source_handle, post, False, result)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Post the latest configured Courts of NZ source item to Threads only."
    )
    parser.add_argument("--config-path", default="config.json")
    parser.add_argument("--delivery-state-path", default="conductor/target_delivery_state.json")
    parser.add_argument("--backlog-state-path", default="conductor/bluesky_backlog_state.json")
    parser.add_argument("--archive-dir", default="historical_archive")
    parser.add_argument(
        "--confirm-live-posting",
        action="store_true",
        help="Actually publish to Threads. Without this flag, only a dry run is emitted.",
    )
    args = parser.parse_args()

    result = run_latest_threads_post(
        config_path=args.config_path,
        delivery_state_path=args.delivery_state_path,
        backlog_state_path=args.backlog_state_path,
        archive_dir=args.archive_dir,
        dry_run=not args.confirm_live_posting,
    )
    print(json.dumps(asdict(result), indent=2, ensure_ascii=False, sort_keys=True))


def _build_threads_adapter() -> ThreadsApiAdapter:
    user_id = os.getenv("THREADS_USER_ID") or os.getenv("THREADS_MIRROR_ACCOUNT_ID")
    access_token = os.getenv("THREADS_ACCESS_TOKEN")
    if not user_id or not access_token:
        raise RuntimeError("Missing THREADS_ACCESS_TOKEN and THREADS_USER_ID.")
    return ThreadsApiAdapter(
        user_id,
        access_token,
        api_base_url=os.getenv("THREADS_API_BASE_URL", "https://graph.threads.net/v1.0"),
    )


def _already_delivered(
    state: TargetDeliveryState,
    source_handle: str,
    post_id: str,
) -> bool:
    return post_id in set(
        state.get("delivered_post_ids", {}).get("threads", {}).get(source_handle, [])
    )


def _mark_delivered(
    state: TargetDeliveryState,
    source_handle: str,
    post_id: str,
) -> None:
    delivered_by_target = state.setdefault("delivered_post_ids", {})
    delivered_by_handle = delivered_by_target.setdefault("threads", {})
    delivered_posts = delivered_by_handle.setdefault(source_handle, [])
    if post_id not in delivered_posts:
        delivered_posts.append(post_id)


def _from_syndication_result(
    source_handle: str,
    post: dict[str, Any],
    dry_run: bool,
    result: SyndicationResult,
) -> ThreadsLatestPostResult:
    return ThreadsLatestPostResult(
        source_handle=source_handle,
        post_id=str(post["post_id"]),
        source_url=str(post["url"]),
        dry_run=dry_run,
        skipped=result.skipped,
        success=result.success,
        detail=result.detail,
    )


def _redact(payload: dict[str, str]) -> dict[str, str]:
    redacted = dict(payload)
    if "access_token" in redacted:
        redacted["access_token"] = "<redacted>"
    return redacted


if __name__ == "__main__":
    main()
