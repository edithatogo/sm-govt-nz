import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypedDict

from src.bluesky import BlueskyPost
from src.config import AppConfig, load_config
from src.syndication import SyndicationAdapter, SyndicationResult, build_adapters_from_env


class ArchiveMirrorState(TypedDict):
    posted_record_ids: dict[str, dict[str, list[str]]]


@dataclass(frozen=True)
class ArchiveReplayRecord:
    source_key: str
    record_id: str
    created_at: str
    content: str
    source_url: str
    source_platform: str
    media_urls: list[str] = field(default_factory=list)


@dataclass
class ArchiveMirrorBacklogSummary:
    selected: int
    posted: int
    results: list[SyndicationResult] = field(default_factory=list)


def run_archive_mirror_backlog(
    config: AppConfig,
    state: ArchiveMirrorState,
    *,
    target: str,
    normalized_archive_dir: str | Path = "historical_archive_normalized",
    adapters: dict[str, SyndicationAdapter] | None = None,
    dry_run: bool = False,
) -> tuple[ArchiveMirrorBacklogSummary, ArchiveMirrorState]:
    target_config = config["syndication_targets"].get(target, {})
    if not target_config.get("enabled", False) or not target_config.get("archive_replay_enabled", False):
        return ArchiveMirrorBacklogSummary(selected=0, posted=0), state

    sources = target_config.get("archive_replay_sources", ["x"])
    records = _load_archive_replay_records(normalized_archive_dir, sources=sources)
    posted_state = {
        target_name: {
            source_key: list(record_ids)
            for source_key, record_ids in posted_by_source.items()
        }
        for target_name, posted_by_source in state.get("posted_record_ids", {}).items()
    }
    next_state: ArchiveMirrorState = {"posted_record_ids": posted_state}
    posted_by_source = next_state["posted_record_ids"].setdefault(target, {})

    selected = _select_unposted_records(
        records,
        posted_by_source,
        limit=_positive_int(target_config.get("archive_replay_max_posts_per_run"), default=1),
    )
    adapter = None
    if not dry_run and selected:
        adapter = (adapters if adapters is not None else build_adapters_from_env([target])).get(target)
        if adapter is None:
            raise RuntimeError(f"Missing syndication adapter configuration for: {target}")

    results: list[SyndicationResult] = []
    posted_count = 0
    for record in selected:
        post = _archive_replay_record_to_post(record)
        if dry_run:
            result = SyndicationResult(target, success=True, skipped=True, detail="dry-run")
        else:
            assert adapter is not None
            result = adapter.send(post)
        results.append(result)
        if result.success and not result.skipped:
            posted_count += 1
            posted_by_source.setdefault(record.source_key, []).append(record.record_id)

    return ArchiveMirrorBacklogSummary(selected=len(selected), posted=posted_count, results=results), next_state


def load_archive_mirror_state(
    state_path: str | Path = "conductor/archive_mirror_state.json",
) -> ArchiveMirrorState:
    path = Path(state_path)
    if not path.exists():
        return {"posted_record_ids": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if "posted_record_ids" not in data:
        raise ValueError("Invalid archive mirror state: Must contain posted_record_ids.")
    return data


def save_archive_mirror_state(
    state: ArchiveMirrorState,
    state_path: str | Path = "conductor/archive_mirror_state.json",
) -> None:
    path = Path(state_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(state, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(
    *,
    target: str = "bluesky",
    config_path: str = "config.json",
    state_path: str = "conductor/archive_mirror_state.json",
    dry_run: bool = False,
) -> ArchiveMirrorBacklogSummary:
    config = load_config(config_path)
    state = load_archive_mirror_state(state_path)
    summary, next_state = run_archive_mirror_backlog(
        config,
        state,
        target=target,
        dry_run=dry_run,
    )
    if not dry_run:
        save_archive_mirror_state(next_state, state_path)
    return summary


def _load_archive_replay_records(
    normalized_archive_dir: str | Path,
    *,
    sources: list[str],
) -> list[ArchiveReplayRecord]:
    records: list[ArchiveReplayRecord] = []
    if "x" in sources:
        x_root = Path(normalized_archive_dir) / "x"
        records.extend(_load_x_replay_records(x_root))
    return sorted(records, key=lambda record: (record.created_at, record.record_id))


def _load_x_replay_records(root: Path) -> list[ArchiveReplayRecord]:
    if not root.exists():
        return []
    records: list[ArchiveReplayRecord] = []
    for shard in sorted(root.glob("*.jsonl")):
        for line in shard.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            data: dict[str, Any] = json.loads(line)
            if data.get("source_platform") != "x":
                continue
            source_account = str(data.get("source_account", "")).strip()
            record_id = str(data.get("record_id", "")).strip()
            if not source_account or not record_id:
                continue
            records.append(
                ArchiveReplayRecord(
                    source_key=f"x:{source_account}",
                    record_id=record_id,
                    created_at=str(data.get("original_created_at", "")),
                    content=str(data.get("content", "")),
                    source_url=str(data.get("source_url") or data.get("canonical_url", "")),
                    source_platform="x",
                    media_urls=[
                        str(media.get("url"))
                        for media in data.get("media_refs", [])
                        if isinstance(media, dict) and media.get("url")
                    ],
                )
            )
    return records


def _select_unposted_records(
    records: list[ArchiveReplayRecord],
    posted_by_source: dict[str, list[str]],
    *,
    limit: int,
) -> list[ArchiveReplayRecord]:
    selected: list[ArchiveReplayRecord] = []
    for record in records:
        if record.record_id in set(posted_by_source.get(record.source_key, [])):
            continue
        selected.append(record)
        if len(selected) >= limit:
            break
    return selected


def _archive_replay_record_to_post(record: ArchiveReplayRecord) -> BlueskyPost:
    source_date = record.created_at[:10] if record.created_at else "unknown date"
    text = f"Archived {record.source_platform.upper()} post from {source_date}:\n\n{record.content}"
    return {
        "post_id": record.record_id,
        "uri": "",
        "cid": "",
        "handle": record.source_key,
        "author_did": "",
        "text": text,
        "created_at": record.created_at,
        "url": record.source_url,
        "images": [
            {"alt": "", "fullsize": media_url, "thumb": media_url}
            for media_url in record.media_urls
        ],
    }


def _positive_int(value: object, *, default: int) -> int:
    return value if isinstance(value, int) and value > 0 else default
