from dataclasses import dataclass, field
from typing import Iterable

from src.archiver import archive_bluesky_post, write_timeline
from src.bluesky import AuthorFeedClient, BlueskyPost, fetch_new_posts_for_account
from src.config import (
    AppConfig,
    AppState,
    TargetDeliveryState,
    load_backlog_state,
    load_config,
    load_state,
    load_target_delivery_state,
    save_state,
    save_target_delivery_state,
)
from src.syndication import SyndicationAdapter, SyndicationResult, build_adapters_from_env
from src.threads_pipeline import get_threads_pipeline_status


@dataclass
class AccountRunResult:
    handle: str
    fetched: int
    syndicated: int
    latest_post_id: str
    results: list[SyndicationResult] = field(default_factory=list)


@dataclass
class RunSummary:
    accounts: list[AccountRunResult]

    @property
    def fetched(self) -> int:
        return sum(account.fetched for account in self.accounts)

    @property
    def syndicated(self) -> int:
        return sum(account.syndicated for account in self.accounts)


def run_syndication(
    config: AppConfig,
    state: AppState,
    *,
    feed_client: AuthorFeedClient | None = None,
    adapters: dict[str, SyndicationAdapter] | None = None,
    dry_run: bool = False,
    archive_dir: str = "historical_archive",
    backlog_state_path: str = "conductor/bluesky_backlog_state.json",
    backlog_archive_dir: str = "historical_archive",
    delivery_state: TargetDeliveryState | None = None,
) -> tuple[RunSummary, AppState]:
    active_targets = _active_targets(
        config,
        backlog_state_path=backlog_state_path,
        backlog_archive_dir=backlog_archive_dir,
    )
    available_adapters = adapters if adapters is not None else build_adapters_from_env(active_targets)
    next_state: AppState = {"last_seen_post_ids": dict(state["last_seen_post_ids"])}
    target_delivery_state = delivery_state if delivery_state is not None else {"delivered_post_ids": {}}
    account_results: list[AccountRunResult] = []
    archived_any = False

    for account in config["monitored_accounts"]:
        handle = account["handle"]
        last_seen = state["last_seen_post_ids"].get(handle, "")
        account_targets = _enabled_account_targets(account["syndicate_to"], active_targets)
        if not account_targets:
            account_results.append(
                AccountRunResult(
                    handle=handle,
                    fetched=0,
                    syndicated=0,
                    latest_post_id=last_seen,
                    results=[],
                )
            )
            continue
        posts = fetch_new_posts_for_account(account, last_seen, client=feed_client)

        # Registry-aware opt-out check
        agency_id = account.get("agency_id")
        if agency_id and not _should_syndicate(agency_id, config):
            account_results.append(
                AccountRunResult(
                    handle=handle,
                    fetched=len(posts),
                    syndicated=0,
                    latest_post_id=last_seen,
                    results=[SyndicationResult("all", success=True, skipped=True, detail="opted-out")],
                )
            )
            continue

        posts = _limit_posts_for_enabled_targets(
            posts,
            account["syndicate_to"],
            config,
            active_targets=active_targets,
        )
        result_items: list[SyndicationResult] = []
        syndicated_count = 0
        failed_delivery = False

        for post in posts:
            if not dry_run:
                archive_bluesky_post(post, archive_dir=archive_dir)
                archived_any = True
            for target in account_targets:
                if _already_delivered(target_delivery_state, target, handle, post["post_id"]):
                    result_items.append(
                        SyndicationResult(target, success=True, skipped=True, detail="duplicate")
                    )
                    continue
                adapter = available_adapters.get(target)
                if adapter is None:
                    result_items.append(
                        SyndicationResult(target, success=False, skipped=True, detail="not configured")
                    )
                    failed_delivery = True
                    continue
                result = _send_with_isolation(adapter, target, post)
                result_items.append(result)
                if result.success and not result.skipped:
                    syndicated_count += 1
                    if not dry_run:
                        _mark_delivered(target_delivery_state, target, handle, post["post_id"])
                if not result.success:
                    failed_delivery = True

        latest_post_id = posts[-1]["post_id"] if posts else last_seen
        if posts and not dry_run and not failed_delivery:
            next_state["last_seen_post_ids"][handle] = latest_post_id

        account_results.append(
            AccountRunResult(
                handle=handle,
                fetched=len(posts),
                syndicated=syndicated_count,
                latest_post_id=latest_post_id,
                results=result_items,
            )
        )

    if archived_any:
        write_timeline(archive_dir)

    return RunSummary(account_results), next_state


def _send_with_isolation(
    adapter: SyndicationAdapter,
    target: str,
    post: BlueskyPost,
) -> SyndicationResult:
    try:
        return adapter.send(post)
    except Exception as error:
        return SyndicationResult(
            target,
            success=False,
            detail=f"{type(error).__name__}: {error}",
        )


def main(
    config_path: str = "config.json",
    state_path: str = "conductor/state.json",
    *,
    dry_run: bool = False,
    delivery_state_path: str = "conductor/target_delivery_state.json",
) -> RunSummary:
    config = load_config(config_path)
    state = load_state(state_path)
    delivery_state = load_target_delivery_state(delivery_state_path)
    summary, next_state = run_syndication(
        config,
        state,
        dry_run=dry_run,
        delivery_state=delivery_state,
    )
    if not dry_run:
        save_state(next_state, state_path)
        save_target_delivery_state(delivery_state, delivery_state_path)
    return summary


def _enabled_account_targets(account_targets: Iterable[str], active_targets: Iterable[str]) -> list[str]:
    active = set(active_targets)
    return [target for target in account_targets if target in active]


def _should_syndicate(agency_id: str, config: AppConfig) -> bool:
    opt_outs = config.get("syndication_opt_outs", [])
    return agency_id not in set(str(item) for item in opt_outs)


def _already_delivered(
    state: TargetDeliveryState,
    target: str,
    handle: str,
    post_id: str,
) -> bool:
    return post_id in set(state.get("delivered_post_ids", {}).get(target, {}).get(handle, []))


def _mark_delivered(
    state: TargetDeliveryState,
    target: str,
    handle: str,
    post_id: str,
) -> None:
    delivered_by_target = state.setdefault("delivered_post_ids", {})
    delivered_by_handle = delivered_by_target.setdefault(target, {})
    delivered_posts = delivered_by_handle.setdefault(handle, [])
    if post_id not in delivered_posts:
        delivered_posts.append(post_id)


def _active_targets(
    config: AppConfig,
    *,
    backlog_state_path: str,
    backlog_archive_dir: str,
) -> list[str]:
    active_targets: list[str] = []
    backlog_state = None
    for name, target_config in config["syndication_targets"].items():
        if not target_config.get("enabled", False):
            continue
        if target_config.get("gated_by") == "bluesky_backlog_complete":
            if backlog_state is None:
                backlog_state = load_backlog_state(backlog_state_path)
            status = get_threads_pipeline_status(
                config,
                backlog_state,
                archive_dir=backlog_archive_dir,
                source_handle=config["monitored_accounts"][0]["handle"],
            )
            if not status.ready_for_threads_posting:
                continue
        active_targets.append(name)
    return active_targets


def _limit_posts_for_enabled_targets(
    posts: list[BlueskyPost],
    account_targets: Iterable[str],
    config: AppConfig,
    *,
    active_targets: Iterable[str] | None = None,
) -> list[BlueskyPost]:
    limits = []
    active_target_set = (
        set(active_targets)
        if active_targets is not None
        else {
            name
            for name, target_config in config["syndication_targets"].items()
            if target_config.get("enabled", False)
        }
    )
    for target in account_targets:
        if target not in active_target_set:
            continue
        limit = config["syndication_targets"].get(target, {}).get("max_posts_per_run")
        if isinstance(limit, int) and limit > 0:
            limits.append(limit)

    if not limits:
        return posts
    return posts[: min(limits)]


if __name__ == "__main__":
    result = main()
    print(f"Fetched {result.fetched} posts; syndicated {result.syndicated} deliveries.")
