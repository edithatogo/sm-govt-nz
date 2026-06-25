import tarfile
import json
from pathlib import Path

import pyarrow.parquet as pq

from scripts.publish_archives import (
    BundleManifest,
    create_archive_bundle,
    publish_to_hugging_face,
    publish_to_zenodo,
    publish_to_zenodo_deposition,
    publish_from_env,
    write_publication_status_report,
    _requested_publish_targets,
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
    zenodo_deposition = publish_to_zenodo_deposition(
        bundle,
        "zenodo-token",
        api_url="https://zenodo.example/api/deposit/depositions",
        uploader=uploader,
    )
    huggingface = publish_to_hugging_face(bundle, "hf-token", "org/dataset", uploader)

    assert zenodo["url"] == "https://zenodo.example/api"
    assert zenodo_deposition["url"] == "https://zenodo.example/api/deposit/depositions"
    assert huggingface["url"] == "https://huggingface.co/api/datasets/org/dataset/upload"
    assert uploader.calls[0][3]["file_count"] == 2
    assert uploader.calls[1][3]["metadata"]["upload_type"] == "dataset"


def test_requested_publish_targets_keep_manual_default_artifact_only() -> None:
    assert _requested_publish_targets(False, "artifact") == []
    assert _requested_publish_targets(True, "artifact") == ["huggingface", "zenodo"]
    assert _requested_publish_targets(True, "huggingface") == ["huggingface"]
    assert _requested_publish_targets(True, "zenodo") == ["zenodo"]
    assert _requested_publish_targets(True, "all") == ["huggingface", "zenodo"]


def test_publish_from_env_can_publish_huggingface_without_zenodo(monkeypatch) -> None:
    calls = []

    def fake_hf(bundle, token, repo_id):
        calls.append(("hf", token, repo_id))
        return {"repo_id": repo_id, "paths_in_repo": ["README.md"]}

    def fake_zenodo(*args, **kwargs):
        calls.append(("zenodo",))
        return {"deposition_id": 1}

    monkeypatch.setenv("HF_TOKEN", "hf-token")
    monkeypatch.setenv("HF_DATASET_REPO_ID", "org/dataset")
    monkeypatch.setenv("ZENODO_TOKEN", "zen-token")
    monkeypatch.setattr("scripts.publish_archives.publish_to_hugging_face", fake_hf)
    monkeypatch.setattr("scripts.publish_archives.publish_to_zenodo_deposition", fake_zenodo)

    result = publish_from_env(
        BundleManifest("bundle.tar.gz", "a" * 64, 2, 120),
        targets={"huggingface"},
    )

    assert result == {"huggingface": {"repo_id": "org/dataset", "paths_in_repo": ["README.md"]}}
    assert calls == [("hf", "hf-token", "org/dataset")]


def test_write_publication_status_report_records_artifact_and_targets(tmp_path) -> None:
    path = tmp_path / "publication-status.json"
    bundle = BundleManifest(
        bundle_path="dist/historical_archive.tar.gz",
        sha256="a" * 64,
        file_count=2,
        uncompressed_bytes=120,
        normalized_record_count=1,
        raw_file_count=3,
    )

    write_publication_status_report(
        bundle=bundle,
        path=path,
        mode="published",
        requested_targets=["huggingface"],
        publication_results={"huggingface": {"repo_id": "org/dataset"}},
    )

    report = json.loads(path.read_text(encoding="utf-8"))
    assert report["mode"] == "published"
    assert report["requested_targets"] == ["huggingface"]
    assert report["artifact"]["normalized_record_count"] == 1
    assert "source_git" in report
    assert report["hugging_face"]["status"] == "published"
    assert report["hugging_face"]["target"] == "org/dataset"
    assert report["zenodo"]["status"] == "not_requested_or_not_configured"

