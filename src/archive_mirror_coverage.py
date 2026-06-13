import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from src.archiver import iter_archive_records
from src.config import load_backlog_state


@dataclass(frozen=True)
class SourceArchiveCoverage:
    source_key: str
    source_platform: str
    source_account: str
    total_records: int


@dataclass(frozen=True)
class TargetArchiveCoverage:
    target: str
    total_source_records: int
    posted_records: int
    remaining_records: int
    supports_backdating: bool
    note: str = ""
    remaining_by_source: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class ArchiveMirrorCoverageReport:
    sources: list[SourceArchiveCoverage]
    targets: list[TargetArchiveCoverage]

    @property
    def complete(self) -> bool:
        return all(target.remaining_records == 0 for target in self.targets)

    def to_dict(self) -> dict[str, Any]:
        return {
            "complete": self.complete,
            "sources": [asdict(source) for source in self.sources],
            "targets": [asdict(target) for target in self.targets],
        }


def build_archive_mirror_coverage_report(
    *,
    archive_dir: str | Path = "historical_archive",
    normalized_archive_dir: str | Path = "historical_archive_normalized",
    bluesky_state_path: str | Path = "conductor/bluesky_backlog_state.json",
    archive_mirror_state_path: str | Path = "conductor/archive_mirror_state.json",
    threads_state_path: str | Path = "conductor/threads_backlog_state.json",
) -> ArchiveMirrorCoverageReport:
    source_records = _load_source_record_ids(archive_dir, normalized_archive_dir)
    sources = [
        SourceArchiveCoverage(
            source_key=source_key,
            source_platform=source_key.split(":", 1)[0],
            source_account=source_key.split(":", 1)[1],
            total_records=len(record_ids),
        )
        for source_key, record_ids in sorted(source_records.items())
    ]

    total_records = sum(len(record_ids) for record_ids in source_records.values())
    targets = [
        _target_coverage(
            target="bluesky",
            source_records=source_records,
            posted_by_source=_merge_posted_by_source(
                _load_bluesky_posted_by_source(bluesky_state_path),
                _load_target_posted_by_source(archive_mirror_state_path, "bluesky"),
            ),
            supports_backdating=False,
            note=(
                "Bluesky posts are published as current mirror posts; original "
                "source timestamps are preserved in repo archive metadata."
            ),
        ),
        _target_coverage(
            target="threads",
            source_records=source_records,
            posted_by_source=_merge_posted_by_source(
                _load_generic_posted_by_source(threads_state_path),
                _load_target_posted_by_source(archive_mirror_state_path, "threads"),
            ),
            supports_backdating=False,
            note=(
                "Threads publishing does not expose a supported backdated "
                "publication timestamp in the configured pipeline; original "
                "timestamps must be preserved in mirror text and archive metadata."
            ),
        ),
    ]
    assert all(target.total_source_records == total_records for target in targets)
    return ArchiveMirrorCoverageReport(sources=sources, targets=targets)


def write_archive_mirror_coverage_report(
    output_path: str | Path = "conductor/archive_mirror_coverage.json",
    **kwargs: Any,
) -> ArchiveMirrorCoverageReport:
    report = build_archive_mirror_coverage_report(**kwargs)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report.to_dict(), indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def _load_source_record_ids(
    archive_dir: str | Path,
    normalized_archive_dir: str | Path,
) -> dict[str, set[str]]:
    sources: dict[str, set[str]] = {}

    for record in iter_archive_records(archive_dir):
        agency = str(record.get("agency", "")).strip()
        post_id = str(record.get("post_id", "")).strip()
        if agency and post_id:
            sources.setdefault(f"bluesky:{agency}", set()).add(post_id)

    x_root = Path(normalized_archive_dir) / "x"
    if x_root.exists():
        for shard in sorted(x_root.glob("*.jsonl")):
            for line in shard.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                record = json.loads(line)
                if record.get("source_platform") != "x":
                    continue
                account = str(record.get("source_account", "")).strip()
                record_id = str(record.get("record_id", "")).strip()
                if account and record_id:
                    sources.setdefault(f"x:{account}", set()).add(record_id)

    return sources


def _load_bluesky_posted_by_source(state_path: str | Path) -> dict[str, set[str]]:
    state = load_backlog_state(str(state_path))
    return {
        f"bluesky:{source_account}": set(post_ids)
        for source_account, post_ids in state.get("posted_post_ids", {}).items()
    }


def _load_generic_posted_by_source(state_path: str | Path) -> dict[str, set[str]]:
    path = Path(state_path)
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    raw_posted = data.get("posted_record_ids", {})
    if not isinstance(raw_posted, dict):
        raise ValueError(f"Invalid mirror state: {state_path} must contain posted_record_ids.")
    return {
        str(source_key): {str(record_id) for record_id in record_ids}
        for source_key, record_ids in raw_posted.items()
        if isinstance(record_ids, list)
    }


def _load_target_posted_by_source(
    state_path: str | Path,
    target: str,
) -> dict[str, set[str]]:
    path = Path(state_path)
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    posted_by_target = data.get("posted_record_ids", {})
    if not isinstance(posted_by_target, dict):
        raise ValueError(f"Invalid archive mirror state: {state_path} must contain posted_record_ids.")
    raw_posted = posted_by_target.get(target, {})
    if not isinstance(raw_posted, dict):
        return {}
    return {
        str(source_key): {str(record_id) for record_id in record_ids}
        for source_key, record_ids in raw_posted.items()
        if isinstance(record_ids, list)
    }


def _merge_posted_by_source(
    *states: dict[str, set[str]],
) -> dict[str, set[str]]:
    merged: dict[str, set[str]] = {}
    for state in states:
        for source_key, record_ids in state.items():
            merged.setdefault(source_key, set()).update(record_ids)
    return merged


def _target_coverage(
    *,
    target: str,
    source_records: dict[str, set[str]],
    posted_by_source: dict[str, set[str]],
    supports_backdating: bool,
    note: str,
) -> TargetArchiveCoverage:
    remaining_by_source = {
        source_key: len(record_ids - posted_by_source.get(source_key, set()))
        for source_key, record_ids in source_records.items()
    }
    total = sum(len(record_ids) for record_ids in source_records.values())
    remaining = sum(remaining_by_source.values())
    return TargetArchiveCoverage(
        target=target,
        total_source_records=total,
        posted_records=total - remaining,
        remaining_records=remaining,
        supports_backdating=supports_backdating,
        note=note,
        remaining_by_source=dict(sorted(remaining_by_source.items())),
    )
