import json

from src.archive_mirror_coverage import build_archive_mirror_coverage_report


def test_archive_mirror_coverage_counts_bluesky_and_x_sources(tmp_path) -> None:
    archive_dir = tmp_path / "historical_archive" / "courtsofnz.bsky.social"
    archive_dir.mkdir(parents=True)
    write_legacy_bluesky_record(archive_dir, "bsky-1")
    write_legacy_bluesky_record(archive_dir, "bsky-2")

    normalized_x_dir = tmp_path / "historical_archive_normalized" / "x"
    normalized_x_dir.mkdir(parents=True)
    (normalized_x_dir / "2020-01.jsonl").write_text(
        json.dumps(
            {
                "record_id": "x:123",
                "source_platform": "x",
                "source_account": "CourtsofNZ",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    state_path = tmp_path / "bluesky_backlog_state.json"
    state_path.write_text(
        json.dumps({"posted_post_ids": {"courtsofnz.bsky.social": ["bsky-1"]}}),
        encoding="utf-8",
    )

    report = build_archive_mirror_coverage_report(
        archive_dir=tmp_path / "historical_archive",
        normalized_archive_dir=tmp_path / "historical_archive_normalized",
        bluesky_state_path=state_path,
        threads_state_path=tmp_path / "missing_threads_state.json",
    )

    assert {source.source_key: source.total_records for source in report.sources} == {
        "bluesky:courtsofnz.bsky.social": 2,
        "x:CourtsofNZ": 1,
    }
    bluesky = next(target for target in report.targets if target.target == "bluesky")
    threads = next(target for target in report.targets if target.target == "threads")
    assert bluesky.posted_records == 1
    assert bluesky.remaining_by_source == {
        "bluesky:courtsofnz.bsky.social": 1,
        "x:CourtsofNZ": 1,
    }
    assert threads.posted_records == 0
    assert threads.remaining_records == 3
    assert threads.supports_backdating is False
    assert report.complete is False
    assert report.is_target_complete("bluesky") is False


def test_archive_mirror_coverage_reports_bluesky_completion_independently(
    tmp_path,
) -> None:
    archive_dir = tmp_path / "historical_archive" / "courtsofnz.bsky.social"
    archive_dir.mkdir(parents=True)
    write_legacy_bluesky_record(archive_dir, "bsky-1")

    normalized_x_dir = tmp_path / "historical_archive_normalized" / "x"
    normalized_x_dir.mkdir(parents=True)
    (normalized_x_dir / "2020-01.jsonl").write_text(
        json.dumps(
            {
                "record_id": "x:123",
                "source_platform": "x",
                "source_account": "CourtsofNZ",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    bluesky_state_path = tmp_path / "bluesky_backlog_state.json"
    bluesky_state_path.write_text(
        json.dumps({"posted_post_ids": {"courtsofnz.bsky.social": ["bsky-1"]}}),
        encoding="utf-8",
    )

    archive_state_path = tmp_path / "archive_mirror_state.json"
    archive_state_path.write_text(
        json.dumps(
            {
                "posted_record_ids": {
                    "bluesky": {
                        "x:CourtsofNZ": ["x:123"],
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    report = build_archive_mirror_coverage_report(
        archive_dir=tmp_path / "historical_archive",
        normalized_archive_dir=tmp_path / "historical_archive_normalized",
        bluesky_state_path=bluesky_state_path,
        archive_mirror_state_path=archive_state_path,
        threads_state_path=tmp_path / "missing_threads_state.json",
    )

    bluesky = next(target for target in report.targets if target.target == "bluesky")
    threads = next(target for target in report.targets if target.target == "threads")
    assert bluesky.remaining_records == 0
    assert threads.remaining_records == 2
    assert report.is_target_complete("bluesky") is True
    assert report.complete is True


def write_legacy_bluesky_record(directory, post_id: str) -> None:
    (directory / f"{post_id}.json").write_text(
        json.dumps(
            {
                "agency": "courtsofnz.bsky.social",
                "post_id": post_id,
                "created_at": "2026-06-10T00:00:00Z",
                "content": "Court notice",
                "source_url": f"https://bsky.app/profile/courtsofnz.bsky.social/post/{post_id}",
                "images": [],
                "media_urls": [],
                "edit_history": [],
            }
        ),
        encoding="utf-8",
    )
