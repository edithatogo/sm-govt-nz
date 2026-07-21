import hashlib
import io
import json
import tarfile
from pathlib import Path

from scripts.migrate_git_lfs_to_huggingface import hydrate_archive, migrate_lfs_payloads


class FakeApi:
    def __init__(self) -> None:
        self.uploads = []

    def create_repo(self, **kwargs) -> None:
        self.repo = kwargs

    def upload_file(self, **kwargs) -> None:
        self.uploads.append(kwargs)


def write_pointer(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "version https://git-lfs.github.com/spec/v1",
                f"oid sha256:{hashlib.sha256(payload).hexdigest()}",
                f"size {len(payload)}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_migration_verifies_uploads_then_removes_lfs_pointer(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    payload = b'{"record_id":"website:1","text":"archived"}\n'
    pointer = Path("historical_archive_normalized/website/2026-07.jsonl")
    write_pointer(pointer, payload)
    Path(".gitattributes").write_text(
        "historical_archive_normalized/website/*.jsonl filter=lfs diff=lfs merge=lfs -text\n",
        encoding="utf-8",
    )
    bundle = Path("bundle.tar.gz")
    with tarfile.open(bundle, "w:gz") as archive:
        info = tarfile.TarInfo("normalized/website/2026-07.jsonl")
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))
    api = FakeApi()

    manifest = migrate_lfs_payloads(
        repo_id="owner/dataset",
        bundle_path_in_repo="bundles/historical_archive.tar.gz",
        normalized_root=Path("historical_archive_normalized"),
        manifest_path=Path("conductor/huggingface_lfs_migration_manifest.json"),
        destination_prefix="archive",
        token="test-token",
        cleanup=True,
        download=lambda repo_id, path, token: bundle,
        api=api,
    )

    assert manifest["entries"][0]["oid"] == hashlib.sha256(payload).hexdigest()
    assert not pointer.exists()
    assert "filter=lfs" not in Path(".gitattributes").read_text(encoding="utf-8")
    assert [upload["path_in_repo"] for upload in api.uploads] == [
        "archive/historical_archive_normalized/website/2026-07.jsonl",
        "metadata/git_lfs_migration_manifest.json",
    ]


def test_hydration_merges_hugging_face_baseline_with_git_delta(tmp_path) -> None:
    source_root = tmp_path / "historical_archive_normalized"
    delta = source_root / "website/2026-07.jsonl"
    delta.parent.mkdir(parents=True)
    delta.write_text(
        '{"record_id":"website:1","text":"duplicate"}\n'
        '{"record_id":"website:2","text":"new"}\n',
        encoding="utf-8",
    )
    baseline = tmp_path / "baseline.jsonl"
    baseline.write_text('{"record_id":"website:1","text":"archived"}\n', encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "dataset_repo_id": "owner/dataset",
                "entries": [
                    {
                        "relative_path": "website/2026-07.jsonl",
                        "hf_path": "archive/historical_archive_normalized/website/2026-07.jsonl",
                        "oid": hashlib.sha256(baseline.read_bytes()).hexdigest(),
                        "size": baseline.stat().st_size,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    output_root = tmp_path / "hydrated"

    result = hydrate_archive(
        manifest_path=manifest,
        source_root=source_root,
        output_root=output_root,
        token=None,
        download=lambda repo_id, path, token: baseline,
    )

    records = [json.loads(line) for line in (output_root / "website/2026-07.jsonl").read_text().splitlines()]
    assert result["hydrated_files"] == 1
    assert records == [
        {"record_id": "website:1", "text": "archived"},
        {"record_id": "website:2", "text": "new"},
    ]


def test_publication_workflows_hydrate_without_git_lfs_checkout() -> None:
    workflows = [
        ".github/workflows/pages.yml",
        ".github/workflows/publish_archives.yml",
        ".github/workflows/archive_registered_sources.yml",
        ".github/workflows/archive_threads_manual_seeds.yml",
        ".github/workflows/publish_retrospective_monthly_archive.yml",
    ]
    for workflow_path in workflows:
        workflow = Path(workflow_path).read_text(encoding="utf-8")
        assert "scripts/migrate_git_lfs_to_huggingface.py hydrate" in workflow
        assert "dist/hydrated_archive_normalized" in workflow
        assert "lfs: true" not in workflow

    migration = Path(".github/workflows/migrate_git_lfs_to_huggingface.yml").read_text(encoding="utf-8")
    assert "transfer-git-lfs-to-hugging-face" in migration
    assert "lfs: false" in migration
    assert "--cleanup" in migration
