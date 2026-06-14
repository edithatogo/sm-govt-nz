import json

from scripts.build_archive_compaction_manifest import (
    build_compaction_manifest,
    write_compaction_manifest,
)


def test_build_compaction_manifest_counts_normalized_and_raw_shards(tmp_path) -> None:
    normalized_dir = tmp_path / "historical_archive_normalized" / "bluesky"
    raw_dir = tmp_path / "historical_archive_raw" / "bluesky" / "2026-06"
    normalized_dir.mkdir(parents=True)
    raw_dir.mkdir(parents=True)
    (normalized_dir / "2026-06.jsonl").write_text('{"id": "1"}\n\n{"id": "2"}\n', encoding="utf-8")
    (raw_dir / "post-1.json").write_text('{"raw": 1}', encoding="utf-8")
    (raw_dir / "post-2.json").write_text('{"raw": 2}', encoding="utf-8")

    manifest = build_compaction_manifest(
        normalized_dir=tmp_path / "historical_archive_normalized",
        raw_dir=tmp_path / "historical_archive_raw",
        generated_at="2026-06-14T00:00:00+00:00",
    )

    assert manifest["totals"]["normalized_record_count"] == 2
    assert manifest["totals"]["normalized_shard_count"] == 1
    assert manifest["totals"]["raw_file_count"] == 2
    assert manifest["totals"]["raw_shard_count"] == 1
    assert manifest["normalized"][0]["source"] == "bluesky"
    assert manifest["normalized"][0]["month"] == "2026-06"
    assert len(manifest["normalized"][0]["sha256"]) == 64
    assert manifest["raw"][0]["source"] == "bluesky"
    assert manifest["raw"][0]["month"] == "2026-06"
    assert manifest["raw"][0]["digest_mode"] == "path_size_inventory"
    assert len(manifest["raw"][0]["sha256"]) == 64


def test_write_compaction_manifest_is_stable_for_same_input(tmp_path) -> None:
    normalized_dir = tmp_path / "normalized" / "rss"
    raw_dir = tmp_path / "raw" / "rss" / "2026-06"
    normalized_dir.mkdir(parents=True)
    raw_dir.mkdir(parents=True)
    (normalized_dir / "2026-06.jsonl").write_text('{"id": "a"}\n', encoding="utf-8")
    (raw_dir / "a.json").write_text('{"raw": true}', encoding="utf-8")
    output_path = tmp_path / "manifest.json"

    first = build_compaction_manifest(
        normalized_dir=tmp_path / "normalized",
        raw_dir=tmp_path / "raw",
        generated_at="2026-06-14T00:00:00+00:00",
    )
    second = build_compaction_manifest(
        normalized_dir=tmp_path / "normalized",
        raw_dir=tmp_path / "raw",
        generated_at="2026-06-14T00:00:00+00:00",
    )
    write_compaction_manifest(first, output_path)

    assert first == second
    assert json.loads(output_path.read_text(encoding="utf-8")) == first


def test_build_compaction_manifest_allows_missing_archive_roots(tmp_path) -> None:
    manifest = build_compaction_manifest(
        normalized_dir=tmp_path / "missing-normalized",
        raw_dir=tmp_path / "missing-raw",
        generated_at="2026-06-14T00:00:00+00:00",
    )

    assert manifest["normalized"] == []
    assert manifest["raw"] == []
    assert manifest["totals"]["normalized_record_count"] == 0
    assert manifest["totals"]["raw_file_count"] == 0
