from dataclasses import dataclass

from src.archiver import iter_archive_records
from src.config import AppConfig, BacklogState, load_backlog_state, load_config


@dataclass(frozen=True)
class ThreadsPipelineStatus:
    enabled: bool
    pipeline_stage_enabled: bool
    account_handle: str
    profile_url: str
    bluesky_backlog_total: int
    bluesky_backlog_posted: int
    bluesky_backlog_remaining: int

    @property
    def ready_for_threads_posting(self) -> bool:
        return self.pipeline_stage_enabled and self.bluesky_backlog_remaining == 0

    @property
    def message(self) -> str:
        if not self.pipeline_stage_enabled:
            return "Threads pipeline stage is disabled."
        if self.bluesky_backlog_remaining > 0:
            return (
                "Threads pipeline stage is waiting for Bluesky backlog completion: "
                f"{self.bluesky_backlog_remaining} records remain."
            )
        if not self.enabled:
            return "Threads pipeline stage is ready for API credential implementation."
        return "Threads pipeline stage is ready to post through the configured adapter."


def get_threads_pipeline_status(
    config: AppConfig,
    backlog_state: BacklogState,
    *,
    archive_dir: str = "historical_archive",
    source_handle: str = "courtsofnz.bsky.social",
) -> ThreadsPipelineStatus:
    threads_config = config["syndication_targets"].get("threads", {})
    posted = set(backlog_state.get("posted_post_ids", {}).get(source_handle, []))
    archived = [
        record["post_id"]
        for record in iter_archive_records(archive_dir)
        if record.get("agency") == source_handle and record.get("post_id")
    ]
    remaining = [post_id for post_id in archived if post_id not in posted]

    return ThreadsPipelineStatus(
        enabled=bool(threads_config.get("enabled", False)),
        pipeline_stage_enabled=bool(threads_config.get("pipeline_stage_enabled", False)),
        account_handle=str(threads_config.get("account_handle", "")),
        profile_url=str(threads_config.get("profile_url", "")),
        bluesky_backlog_total=len(archived),
        bluesky_backlog_posted=len(posted),
        bluesky_backlog_remaining=len(remaining),
    )


def main(
    config_path: str = "config.json",
    backlog_state_path: str = "conductor/bluesky_backlog_state.json",
) -> ThreadsPipelineStatus:
    config = load_config(config_path)
    backlog_state = load_backlog_state(backlog_state_path)
    status = get_threads_pipeline_status(config, backlog_state)
    print(status.message)
    print(
        "Threads account: "
        f"{status.account_handle or 'not configured'} "
        f"({status.profile_url or 'no profile URL'})"
    )
    print(
        "Bluesky backlog: "
        f"{status.bluesky_backlog_posted}/{status.bluesky_backlog_total} posted; "
        f"{status.bluesky_backlog_remaining} remaining."
    )
    return status


if __name__ == "__main__":
    main()
