import argparse
import base64
import gzip
import hashlib
import json
import os
import tarfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class BundleManifest:
    bundle_path: str
    sha256: str
    file_count: int
    uncompressed_bytes: int


class HttpUploader(Protocol):
    def upload_file(
        self,
        url: str,
        token: str,
        file_path: Path,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """Upload a file to a remote repository service."""


class UrlLibUploader:
    def upload_file(
        self,
        url: str,
        token: str,
        file_path: Path,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        payload = json.dumps(
            {
                "filename": file_path.name,
                "metadata": metadata,
                "content_base64": base64.b64encode(file_path.read_bytes()).decode("ascii"),
            }
        ).encode("utf-8")
        request = Request(
            url,
            data=payload,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=60) as response:
            body = response.read().decode("utf-8")
        return json.loads(body) if body else {}


def create_archive_bundle(
    archive_dir: str | os.PathLike[str] = "historical_archive",
    output_dir: str | os.PathLike[str] = "dist",
) -> BundleManifest:
    """Create deterministic JSONL and tar.gz bundles from archived post JSON files."""
    source_root = Path(archive_dir)
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    jsonl_path = output_root / "historical_archive.jsonl.gz"
    tar_path = output_root / "historical_archive.tar.gz"
    json_files = sorted(path for path in source_root.glob("**/*.json") if path.is_file())

    uncompressed_bytes = 0
    with gzip.open(jsonl_path, "wt", encoding="utf-8") as jsonl_file:
        for path in json_files:
            payload = json.loads(path.read_text(encoding="utf-8"))
            line = json.dumps(payload, ensure_ascii=False, sort_keys=True)
            uncompressed_bytes += len(line.encode("utf-8"))
            jsonl_file.write(line + "\n")

    with tarfile.open(tar_path, "w:gz") as tar_file:
        tar_file.add(jsonl_path, arcname=jsonl_path.name)
        for path in json_files:
            tar_file.add(path, arcname=str(path.relative_to(source_root)))

    return BundleManifest(
        bundle_path=str(tar_path),
        sha256=_sha256(tar_path),
        file_count=len(json_files),
        uncompressed_bytes=uncompressed_bytes,
    )


def publish_to_zenodo(
    bundle: BundleManifest,
    token: str,
    endpoint: str,
    uploader: HttpUploader | None = None,
) -> dict[str, Any]:
    metadata = {
        "title": "NZ Government Bluesky Syndicator historical archive",
        "upload_type": "dataset",
        "sha256": bundle.sha256,
        "file_count": bundle.file_count,
    }
    if uploader is not None:
        return uploader.upload_file(endpoint, token, Path(bundle.bundle_path), metadata)
    try:
        import requests
    except ImportError:
        return UrlLibUploader().upload_file(endpoint, token, Path(bundle.bundle_path), metadata)
    with Path(bundle.bundle_path).open("rb") as file:
        response = requests.post(
            endpoint,
            headers={"Authorization": f"Bearer {token}"},
            data={"metadata": json.dumps(metadata)},
            files={"file": (Path(bundle.bundle_path).name, file, "application/gzip")},
            timeout=60,
        )
    response.raise_for_status()
    return response.json() if response.content else {}


def publish_to_hugging_face(
    bundle: BundleManifest,
    token: str,
    repo_id: str,
    uploader: HttpUploader | None = None,
) -> dict[str, Any]:
    endpoint = f"https://huggingface.co/api/datasets/{repo_id}/upload"
    metadata = {"repo_id": repo_id, "sha256": bundle.sha256, "file_count": bundle.file_count}
    if uploader is not None:
        return uploader.upload_file(endpoint, token, Path(bundle.bundle_path), metadata)
    try:
        from huggingface_hub import HfApi
    except ImportError:
        return UrlLibUploader().upload_file(endpoint, token, Path(bundle.bundle_path), metadata)
    api = HfApi(token=token)
    path_in_repo = Path(bundle.bundle_path).name
    api.upload_file(
        path_or_fileobj=bundle.bundle_path,
        path_in_repo=path_in_repo,
        repo_id=repo_id,
        repo_type="dataset",
    )
    return {**metadata, "path_in_repo": path_in_repo}


def publish_from_env(bundle: BundleManifest) -> dict[str, Any]:
    results: dict[str, Any] = {}
    zenodo_token = os.getenv("ZENODO_TOKEN")
    zenodo_endpoint = os.getenv("ZENODO_DEPOSIT_ENDPOINT")
    if zenodo_token and zenodo_endpoint:
        results["zenodo"] = publish_to_zenodo(bundle, zenodo_token, zenodo_endpoint)
    hf_token = os.getenv("HF_TOKEN")
    hf_repo_id = os.getenv("HF_DATASET_REPO_ID")
    if hf_token and hf_repo_id:
        results["huggingface"] = publish_to_hugging_face(bundle, hf_token, hf_repo_id)
    return results


def write_manifest(bundle: BundleManifest, path: str | os.PathLike[str]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(bundle.__dict__, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Bundle and optionally publish archives.")
    parser.add_argument("--archive-dir", default="historical_archive")
    parser.add_argument("--output-dir", default="dist")
    parser.add_argument("--manifest", default="dist/archive_manifest.json")
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()

    bundle = create_archive_bundle(args.archive_dir, args.output_dir)
    write_manifest(bundle, args.manifest)
    if args.publish:
        print(json.dumps(publish_from_env(bundle), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
