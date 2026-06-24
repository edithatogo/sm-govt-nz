import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.bluesky import BlueskyApiClient, BlueskyPost, normalize_feed_item
from src.config import load_config, load_target_delivery_state, save_target_delivery_state
from src.syndication import DryRunAdapter, SyndicationResult, build_adapters_from_env


@dataclass(frozen=True)
class BackfillPostResult:
    target: str
    source_handle: str
    post_id: str
    source_url: str
    dry_run: bool
    skipped: bool
    success: bool
    detail: str


def run_backfill(
    *,
    config_path: str,
    delivery_state_path: str,
    post_ids: list[str],
    targets: list[str],
    dry_run: bool,
    feed_limit: int,
) -> list[BackfillPostResult]:
    config = load_config(config_path)
    source = config["monitored_accounts"][0]
    source_handle = source["handle"]
    source_targets = set(source.get("syndicate_to", []))
    configured_targets = config["syndication_targets"]

    for target in targets:
        if target not in source_targets:
            raise RuntimeError(f"{source_handle} is not configured to syndicate to {target}.")
        target_config = configured_targets.get(target, {})
        if not target_config.get("enabled", False):
            raise RuntimeError(f"{target} target is not enabled.")
        if target_config.get("archive_replay_enabled", False) and target != "bluesky":
            raise RuntimeError(f"{target} historical archive replay must remain disabled.")

    client = BlueskyApiClient()
    raw_feed = client.fetch_author_feed(source["did"] or source_handle, limit=feed_limit)
    posts_by_id = {
        post["post_id"]: post
        for post in (normalize_feed_item(item, source_handle) for item in raw_feed)
        if post["post_id"]
    }
    missing = [post_id for post_id in post_ids if post_id not in posts_by_id]
    if missing:
        raise RuntimeError(f"Requested posts were not found in the latest {feed_limit} feed items: {missing}")

    # Preserve source chronology so belated mirrors appear in the same order as the source.
    ordered_posts = [posts_by_id[post_id] for post_id in reversed([p["post_id"] for p in posts_by_id.values()]) if post_id in post_ids]

    delivery_state = load_target_delivery_state(delivery_state_path)
    adapters = (
        {target: DryRunAdapter(target) for target in targets}
        if dry_run
        else build_adapters_from_env(targets)
    )
    results: list[BackfillPostResult] = []

    for post in ordered_posts:
        for target in targets:
            if _already_delivered(delivery_state, target, source_handle, post["post_id"]):
                if not dry_run:
                    _clear_pending(delivery_state, target, source_handle, post["post_id"])
                    save_target_delivery_state(delivery_state, delivery_state_path)
                results.append(_result(target, source_handle, post, dry_run, True, True, "duplicate"))
                continue

            adapter = adapters.get(target)
            if adapter is None:
                results.append(_result(target, source_handle, post, dry_run, True, False, "not configured"))
                continue

            send_result = _send(adapter, post)
            results.append(
                _result(
                    target,
                    source_handle,
                    post,
                    dry_run,
                    send_result.skipped,
                    send_result.success,
                    send_result.detail,
                )
            )
            if send_result.success and not send_result.skipped and not dry_run:
                _mark_delivered(delivery_state, target, source_handle, post["post_id"])
                _clear_pending(delivery_state, target, source_handle, post["post_id"])
                save_target_delivery_state(delivery_state, delivery_state_path)

    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill specific missed Courts of NZ mirror posts to explicit targets."
    )
    parser.add_argument("--config-path", default="config.json")
    parser.add_argument("--delivery-state-path", default="conductor/target_delivery_state.json")
    parser.add_argument("--post-ids", required=True, help="Comma-separated source post IDs.")
    parser.add_argument("--targets", required=True, help="Comma-separated target names.")
    parser.add_argument("--feed-limit", type=int, default=50)
    parser.add_argument(
        "--confirm-live-posting",
        action="store_true",
        help="Actually publish posts. Without this flag, only dry-run records are emitted.",
    )
    args = parser.parse_args()

    results = run_backfill(
        config_path=args.config_path,
        delivery_state_path=args.delivery_state_path,
        post_ids=_split_csv(args.post_ids),
        targets=_split_csv(args.targets),
        dry_run=not args.confirm_live_posting,
        feed_limit=args.feed_limit,
    )
    print(json.dumps([asdict(result) for result in results], indent=2, sort_keys=True))

    failures = [result for result in results if not result.success]
    if failures:
        raise SystemExit(1)


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _already_delivered(state: dict[str, Any], target: str, source_handle: str, post_id: str) -> bool:
    return post_id in set(state.get("delivered_post_ids", {}).get(target, {}).get(source_handle, []))


def _mark_delivered(state: dict[str, Any], target: str, source_handle: str, post_id: str) -> None:
    delivered_by_target = state.setdefault("delivered_post_ids", {})
    delivered_by_handle = delivered_by_target.setdefault(target, {})
    delivered_posts = delivered_by_handle.setdefault(source_handle, [])
    if post_id not in delivered_posts:
        delivered_posts.append(post_id)


def _clear_pending(state: dict[str, Any], target: str, source_handle: str, post_id: str) -> None:
    pending_by_target = state.get("pending_post_ids", {})
    pending_by_handle = pending_by_target.get(target, {})
    pending_posts = pending_by_handle.get(source_handle, [])
    if post_id in pending_posts:
        pending_posts.remove(post_id)
    if not pending_posts and source_handle in pending_by_handle:
        del pending_by_handle[source_handle]
    if not pending_by_handle and target in pending_by_target:
        del pending_by_target[target]


def _send(adapter: Any, post: BlueskyPost) -> SyndicationResult:
    try:
        return adapter.send(post)
    except Exception as error:
        return SyndicationResult(
            getattr(adapter, "name", ""),
            success=False,
            detail=f"{type(error).__name__}: {error}",
        )


def _result(
    target: str,
    source_handle: str,
    post: BlueskyPost,
    dry_run: bool,
    skipped: bool,
    success: bool,
    detail: str,
) -> BackfillPostResult:
    return BackfillPostResult(
        target=target,
        source_handle=source_handle,
        post_id=post["post_id"],
        source_url=post["url"],
        dry_run=dry_run,
        skipped=skipped,
        success=success,
        detail=detail,
    )


if __name__ == "__main__":
    main()
