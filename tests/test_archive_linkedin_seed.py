import json

from scripts.archive_linkedin_seed import archive_linkedin_seed


def test_archive_linkedin_seed_writes_raw_normalized_and_report(tmp_path) -> None:
    seed_path = tmp_path / "linkedin_seed.json"
    seed_path.write_text(
        json.dumps(
            {
                "posts": [
                    {
                        "post_id": "urn:li:activity:123",
                        "url": "https://www.linkedin.com/feed/update/urn:li:activity:123/",
                        "created_at": "2026-06-10T00:00:00Z",
                        "text": "Judgment of public interest",
                        "media": [{"url": "https://example.test/image.jpg", "media_type": "image"}],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    report = archive_linkedin_seed(
        seed_path=seed_path,
        raw_root=tmp_path / "raw" / "linkedin",
        normalized_root=tmp_path / "normalized" / "linkedin",
        report_path=tmp_path / "linkedin_report.json",
        captured_at="2026-06-14T00:00:00+00:00",
    )

    raw_path = tmp_path / "raw" / "linkedin" / "2026-06" / "urnliactivity123.json"
    shard_path = tmp_path / "normalized" / "linkedin" / "2026-06.jsonl"
    record = json.loads(shard_path.read_text(encoding="utf-8").strip())

    assert raw_path.exists()
    assert record["record_id"] == "linkedin:urn:li:activity:123"
    assert record["source_platform"] == "linkedin"
    assert record["extraction_method"] == "manual_seed"
    assert record["media_refs"][0]["media_type"] == "image"
    assert report["record_count"] == 1
    assert json.loads((tmp_path / "linkedin_report.json").read_text(encoding="utf-8")) == report


def test_archive_linkedin_seed_is_idempotent(tmp_path) -> None:
    seed_path = tmp_path / "linkedin_seed.json"
    seed_path.write_text(
        json.dumps(
            [
                {
                    "url": "https://www.linkedin.com/feed/update/urn:li:activity:abc/",
                    "created_at": "2026-06-10T00:00:00Z",
                    "text": "Courts update",
                }
            ]
        ),
        encoding="utf-8",
    )
    kwargs = {
        "seed_path": seed_path,
        "raw_root": tmp_path / "raw" / "linkedin",
        "normalized_root": tmp_path / "normalized" / "linkedin",
        "captured_at": "2026-06-14T00:00:00+00:00",
    }

    archive_linkedin_seed(**kwargs)
    archive_linkedin_seed(**kwargs)

    shard_path = tmp_path / "normalized" / "linkedin" / "2026-06.jsonl"
    assert len(shard_path.read_text(encoding="utf-8").splitlines()) == 1
