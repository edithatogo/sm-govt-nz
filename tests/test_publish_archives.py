import tarfile

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
        assert "agency/post-1.json" in tar_file.getnames()


def test_publishers_use_expected_endpoints() -> None:
    uploader = FakeUploader()
    bundle = BundleManifest("bundle.tar.gz", "a" * 64, 2, 120)

    zenodo = publish_to_zenodo(bundle, "zenodo-token", "https://zenodo.example/api", uploader)
    huggingface = publish_to_hugging_face(bundle, "hf-token", "org/dataset", uploader)

    assert zenodo["url"] == "https://zenodo.example/api"
    assert huggingface["url"] == "https://huggingface.co/api/datasets/org/dataset/upload"
    assert uploader.calls[0][3]["file_count"] == 2
