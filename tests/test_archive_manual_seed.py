import json

from scripts.archive_manual_seed import archive_manual_seed, find_manual_seed_path


def test_archive_manual_seed_writes_platform_specific_records(tmp_path) -> None:
    seed_path = tmp_path / "youtube_seed.json"
    seed_path.write_text(
        json.dumps(
            {
                "posts": [
                    {
                        "post_id": "video-1",
                        "url": "https://www.youtube.com/watch?v=video-1",
                        "created_at": "2026-06-10T00:00:00Z",
                        "text": "Public video update",
                        "media": [{"url": "https://i.ytimg.com/vi/video-1/default.jpg", "media_type": "thumbnail"}],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    report = archive_manual_seed(
        platform="youtube",
        seed_path=seed_path,
        raw_root=tmp_path / "raw",
        normalized_root=tmp_path / "normalized",
        agency_id="agency",
        source_account="Agency YouTube",
        source_kind="social_profile",
        source_id="agency-youtube",
        captured_at="2026-06-14T00:00:00+00:00",
    )

    raw_path = tmp_path / "raw" / "youtube" / "2026-06" / "video-1.json"
    normalized_path = tmp_path / "normalized" / "youtube" / "2026-06.jsonl"
    record = json.loads(normalized_path.read_text(encoding="utf-8"))
    assert raw_path.exists()
    assert report["record_count"] == 1
    assert record["record_id"] == "youtube:video-1"
    assert record["agency_id"] == "agency"
    assert record["source_platform"] == "youtube"
    assert record["cross_source_ids"]["source_id"] == "agency-youtube"


def test_find_manual_seed_path_prefers_source_id_then_agency(tmp_path) -> None:
    root = tmp_path / "manual_archive_seeds"
    platform_dir = root / "facebook"
    platform_dir.mkdir(parents=True)
    agency_seed = platform_dir / "agency.json"
    source_seed = platform_dir / "agency-facebook.json"
    agency_seed.write_text("[]", encoding="utf-8")
    source_seed.write_text("[]", encoding="utf-8")

    path = find_manual_seed_path(
        {"platform": "facebook", "source_id": "agency-facebook", "agency_id": "agency"},
        root,
    )

    assert path == source_seed
