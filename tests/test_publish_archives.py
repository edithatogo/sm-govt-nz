import tarfile
import json
from pathlib import Path

import pyarrow.parquet as pq

from scripts.publish_archives import (
    BundleManifest,
    create_archive_bundle,
    publish_to_hugging_face,
    publish_to_zenodo,
)


class FakeUploader:
    def __init__(self) -> None:
        self.calls = []

    def upload_file(self, url, token, file_path, metadata):
        self.calls.append((url, token, file_path, metadata))
        return {"url": url, "filename": file_path.name}


def test_create_archive_bundle_writes_tar_gz_and_manifest(tmp_path) -> None:
    archive_dir = tmp_path / "historical_archive" / "agency"
    archive_dir.mkdir(parents=True)
    (archive_dir / "post-1.json").write_text('{"post_id": "post-1"}', encoding="utf-8")

    bundle = create_archive_bundle(tmp_path / "historical_archive", tmp_path / "dist")

    assert bundle.file_count == 1
    assert len(bundle.sha256) == 64
    with tarfile.open(bundle.bundle_path, "r:gz") as tar_file:
        assert "historical_archive.jsonl.gz" in tar_file.getnames()
        assert "legacy/agency/post-1.json" in tar_file.getnames()


def test_create_archive_bundle_includes_normalized_raw_and_dataset_metadata(tmp_path) -> None:
    normalized_dir = tmp_path / "historical_archive_normalized" / "bluesky"
    raw_dir = tmp_path / "historical_archive_raw" / "bluesky" / "2026-06"
    state_dir = tmp_path / "conductor"
    normalized_dir.mkdir(parents=True)
    raw_dir.mkdir(parents=True)
    state_dir.mkdir(parents=True)
    (normalized_dir / "2026-06.jsonl").write_text(
        json.dumps(
            {
                "record_id": "post-1",
                "source_platform": "bluesky",
                "source_account": "courtsofnz.bsky.social",
                "source_url": "https://bsky.app/profile/courtsofnz.bsky.social/post/post-1",
                "original_created_at": "2026-06-01T00:00:00Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (raw_dir / "post-1.json").write_text('{"raw": true}', encoding="utf-8")
    (state_dir / "bluesky_backlog_state.json").write_text(
        json.dumps({"posted_post_ids": {"courtsofnz.bsky.social": ["post-1"]}}),
        encoding="utf-8",
    )
    (state_dir / "archive_mirror_state.json").write_text(
        json.dumps(
            {
                "posted_record_ids": {"bluesky": {"bluesky:courtsofnz.bsky.social": ["post-1"]}},
                "posted_records": {
                    "bluesky": {
                        "bluesky:courtsofnz.bsky.social": [
                            {
                                "detail": "at://did:plc:mirror/app.bsky.feed.post/post-1",
                                "mirror_url": "https://bsky.app/profile/did:plc:mirror/post/post-1",
                                "record_id": "post-1",
                                "source_key": "bluesky:courtsofnz.bsky.social",
                                "status": "posted",
                                "target": "bluesky",
                            }
                        ]
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    bundle = create_archive_bundle(
        tmp_path / "historical_archive",
        tmp_path / "dist",
        tmp_path / "historical_archive_normalized",
        tmp_path / "historical_archive_raw",
    )

    assert bundle.normalized_record_count == 1
    assert bundle.raw_file_count == 1
    assert pq.read_table(bundle.normalized_parquet_path).num_rows == 1
    with tarfile.open(bundle.bundle_path, "r:gz") as tar_file:
        names = tar_file.getnames()
    assert "normalized_archive.jsonl.gz" in names
    assert "normalized_archive.parquet" in names
    assert "corpus_manifest.json" in names
    assert "README.md" in names
    assert "normalized/bluesky/2026-06.jsonl" in names
    assert "raw/bluesky/2026-06/post-1.json" in names

    corpus_manifest = json.loads(Path(bundle.manifest_path).read_text(encoding="utf-8"))
    assert corpus_manifest["record_index"] == [
        {
            "mirror_targets": [
                {
                    "mirror_url": "https://bsky.app/profile/did:plc:mirror/post/post-1",
                    "status": "posted",
                    "target": "bluesky",
                }
            ],
            "original_timestamp": "2026-06-01T00:00:00Z",
            "source_account": "courtsofnz.bsky.social",
            "source_key": "bluesky:courtsofnz.bsky.social",
            "source_platform": "bluesky",
            "source_record_id": "post-1",
            "source_url": "https://bsky.app/profile/courtsofnz.bsky.social/post/post-1",
        }
    ]


def test_publishers_use_expected_endpoints() -> None:
    uploader = FakeUploader()
    bundle = BundleManifest("bundle.tar.gz", "a" * 64, 2, 120)

    zenodo = publish_to_zenodo(bundle, "zenodo-token", "https://zenodo.example/api", uploader)
    huggingface = publish_to_hugging_face(bundle, "hf-token", "org/dataset", uploader)

    assert zenodo["url"] == "https://zenodo.example/api"
    assert huggingface["url"] == "https://huggingface.co/api/datasets/org/dataset/upload"
    assert uploader.calls[0][3]["file_count"] == 2
