from dataclasses import dataclass, field

from src.archiver import PostArchiveSchema, iter_archive_records
from src.bluesky import BlueskyPost
from src.config import (
    AppConfig,
    BacklogState,
    load_backlog_state,
    load_config,
    save_backlog_state,
)
from src.syndication import SyndicationAdapter, SyndicationResult, build_adapters_from_env


@dataclass
class BacklogRunSummary:
    selected: int
    posted: int
    results: list[SyndicationResult] = field(default_factory=list)


def run_bluesky_backlog(
    config: AppConfig,
    state: BacklogState,
    *,
    archive_dir: str = "historical_archive",
    adapters: dict[str, SyndicationAdapter] | None = None,
    dry_run: bool = False,
) -> tuple[BacklogRunSummary, BacklogState]:
    target_config = config["syndication_targets"].get("bluesky", {})
    if not target_config.get("enabled", False) or not target_config.get("backlog_enabled", False):
        return BacklogRunSummary(selected=0, posted=0), state

    available_adapters = adapters if adapters is not None else build_adapters_from_env(["bluesky"])
    adapter = available_adapters.get("bluesky")
    if adapter is None and not dry_run:
        raise RuntimeError("Missing syndication adapter configuration for: bluesky")

    next_state: BacklogState = {
        "posted_post_ids": {
            handle: list(post_ids)
            for handle, post_ids in state.get("posted_post_ids", {}).items()
        }
    }
    results: list[SyndicationResult] = []
    posted_count = 0

    for account in config["monitored_accounts"]:
        if "bluesky" not in account["syndicate_to"]:
            continue
        handle = account["handle"]
        posted_ids = set(next_state["posted_post_ids"].get(handle, []))
        records = _candidate_records(handle, archive_dir, target_config.get("backlog_order", "oldest_first"))
        limit = _positive_int(target_config.get("backlog_max_posts_per_run"), default=1)
        selected = [record for record in records if record["post_id"] not in posted_ids][:limit]

        for record in selected:
            post = _archive_record_to_post(record)
            if dry_run:
                result = SyndicationResult("bluesky", success=True, skipped=True, detail="dry-run")
            else:
                assert adapter is not None
                result = adapter.send(post)
            results.append(result)
            if result.success and not result.skipped:
                posted_count += 1
                if not dry_run:
                    next_state["posted_post_ids"].setdefault(handle, []).append(record["post_id"])

    return BacklogRunSummary(selected=len(results), posted=posted_count, results=results), next_state


def main(
    config_path: str = "config.json",
    state_path: str = "conductor/bluesky_backlog_state.json",
    *,
    dry_run: bool = False,
) -> BacklogRunSummary:
    config = load_config(config_path)
    state = load_backlog_state(state_path)
    summary, next_state = run_bluesky_backlog(config, state, dry_run=dry_run)
    if not dry_run:
        save_backlog_state(next_state, state_path)
    return summary


def _candidate_records(
    handle: str,
    archive_dir: str,
    order: str,
) -> list[PostArchiveSchema]:
    records = [
        record for record in iter_archive_records(archive_dir) if record.get("agency") == handle
    ]
    reverse = order == "newest_first"
    return sorted(
        records,
        key=lambda record: (record.get("created_at", ""), record.get("post_id", "")),
        reverse=reverse,
    )


def _archive_record_to_post(record: PostArchiveSchema) -> BlueskyPost:
    return {
        "post_id": record["post_id"],
        "uri": "",
        "cid": "",
        "handle": record["agency"],
        "author_did": "",
        "text": record["content"],
        "created_at": record["created_at"],
        "url": record["source_url"],
        "images": [
            {
                "alt": str(image.get("alt", "")),
                "fullsize": str(image.get("fullsize", "")),
                "thumb": str(image.get("thumb", "")),
            }
            for image in record.get("images", [])
        ],
    }


def _positive_int(value: object, *, default: int) -> int:
    return value if isinstance(value, int) and value > 0 else default


if __name__ == "__main__":
    result = main()
    print(f"Selected {result.selected} backlog records; posted {result.posted} deliveries.")
