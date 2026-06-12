from dataclasses import dataclass, field
from typing import Iterable

from src.archiver import archive_bluesky_post, write_timeline
from src.bluesky import AuthorFeedClient, BlueskyPost, fetch_new_posts_for_account
from src.config import AppConfig, AppState, load_config, load_state, save_state
from src.syndication import SyndicationAdapter, SyndicationResult, build_adapters_from_env


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
) -> tuple[RunSummary, AppState]:
    active_targets = [
        name
        for name, target_config in config["syndication_targets"].items()
        if target_config.get("enabled", False)
    ]
    available_adapters = adapters if adapters is not None else build_adapters_from_env(active_targets)
    missing_adapters = [
        target for target in active_targets if target not in available_adapters
    ]
    if missing_adapters and not dry_run:
        formatted = ", ".join(sorted(missing_adapters))
        raise RuntimeError(f"Missing syndication adapter configuration for: {formatted}")
    next_state: AppState = {"last_seen_post_ids": dict(state["last_seen_post_ids"])}
    account_results: list[AccountRunResult] = []
    archived_any = False

    for account in config["monitored_accounts"]:
        handle = account["handle"]
        last_seen = state["last_seen_post_ids"].get(handle, "")
        posts = fetch_new_posts_for_account(account, last_seen, client=feed_client)
        posts = _limit_posts_for_enabled_targets(posts, account["syndicate_to"], config)
        result_items: list[SyndicationResult] = []
        syndicated_count = 0

        for post in posts:
            if not dry_run:
                archive_bluesky_post(post, archive_dir=archive_dir)
                archived_any = True
            for target in _enabled_account_targets(account["syndicate_to"], active_targets):
                adapter = available_adapters.get(target)
                if adapter is None:
                    result_items.append(
                        SyndicationResult(target, success=True, skipped=True, detail="not configured")
                    )
                    continue
                result = adapter.send(post)
                result_items.append(result)
                if result.success and not result.skipped:
                    syndicated_count += 1

        latest_post_id = posts[-1]["post_id"] if posts else last_seen
        if posts and not dry_run:
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


def main(
    config_path: str = "config.json",
    state_path: str = "conductor/state.json",
    *,
    dry_run: bool = False,
) -> RunSummary:
    config = load_config(config_path)
    state = load_state(state_path)
    summary, next_state = run_syndication(config, state, dry_run=dry_run)
    if not dry_run:
        save_state(next_state, state_path)
    return summary


def _enabled_account_targets(account_targets: Iterable[str], active_targets: Iterable[str]) -> list[str]:
    active = set(active_targets)
    return [target for target in account_targets if target in active]


def _limit_posts_for_enabled_targets(
    posts: list[BlueskyPost],
    account_targets: Iterable[str],
    config: AppConfig,
) -> list[BlueskyPost]:
    limits = []
    active_targets = {
        name
        for name, target_config in config["syndication_targets"].items()
        if target_config.get("enabled", False)
    }
    for target in account_targets:
        if target not in active_targets:
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
