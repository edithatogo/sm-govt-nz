import argparse
import base64
import gzip
import hashlib
import json
from datetime import datetime, timezone
import os
import subprocess
import tarfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from urllib.request import Request, urlopen


DEFAULT_HF_DATASET_NAME = "corpus-social-media-government-nz"
DEFAULT_HF_DATASET_REPO_ID = "edithatogo/corpus-social-media-government-nz"
DEFAULT_ZENODO_DEPOSIT_API_URL = "https://zenodo.org/api/deposit/depositions"
DEFAULT_OSF_UPLOAD_URL = ""


@dataclass(frozen=True)
class BundleManifest:
    bundle_path: str
    sha256: str
    file_count: int
    uncompressed_bytes: int
    normalized_record_count: int = 0
    raw_file_count: int = 0
    manifest_path: str = ""
    dataset_card_path: str = ""
    normalized_jsonl_path: str = ""
    normalized_parquet_path: str = ""


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
    normalized_dir: str | os.PathLike[str] | None = None,
    raw_dir: str | os.PathLike[str] | None = None,
) -> BundleManifest:
    """Create deterministic corpus bundles from archive files."""
    source_root = Path(archive_dir)
    normalized_root = (
        Path(normalized_dir)
        if normalized_dir is not None
        else source_root.parent / "historical_archive_normalized"
    )
    raw_root = (
        Path(raw_dir) if raw_dir is not None else source_root.parent / "historical_archive_raw"
    )
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    jsonl_path = output_root / "historical_archive.jsonl.gz"
    normalized_jsonl_path = output_root / "normalized_archive.jsonl.gz"
    normalized_parquet_path = output_root / "normalized_archive.parquet"
    tar_path = output_root / "historical_archive.tar.gz"
    corpus_manifest_path = output_root / "corpus_manifest.json"
    dataset_card_path = output_root / "README.md"

    uncompressed_bytes = 0
    legacy_json_files = sorted(path for path in source_root.glob("**/*.json") if path.is_file())
    normalized_jsonl_files = sorted(
        path for path in normalized_root.glob("**/*.jsonl") if path.is_file()
    )
    raw_files = sorted(path for path in raw_root.glob("**/*") if path.is_file())

    with gzip.open(jsonl_path, "wt", encoding="utf-8") as legacy_jsonl_file:
        for path in legacy_json_files:
            payload = json.loads(path.read_text(encoding="utf-8"))
            line = json.dumps(payload, ensure_ascii=False, sort_keys=True)
            uncompressed_bytes += len(line.encode("utf-8"))
            legacy_jsonl_file.write(line + "\n")

    normalized_records = _load_normalized_records(normalized_jsonl_files)
    normalized_record_count = len(normalized_records)
    with gzip.open(normalized_jsonl_path, "wt", encoding="utf-8") as normalized_jsonl_file:
        for record in normalized_records:
            line = json.dumps(record, ensure_ascii=False, sort_keys=True)
            uncompressed_bytes += len(line.encode("utf-8"))
            normalized_jsonl_file.write(line + "\n")
    _write_normalized_parquet(normalized_records, normalized_parquet_path)

    corpus_manifest = _build_corpus_manifest(
        legacy_json_files=legacy_json_files,
        normalized_jsonl_files=normalized_jsonl_files,
        raw_files=raw_files,
        normalized_records=normalized_records,
        jsonl_path=jsonl_path,
        normalized_jsonl_path=normalized_jsonl_path,
        normalized_parquet_path=normalized_parquet_path,
        state_root=source_root.parent / "conductor",
    )
    corpus_manifest_path.write_text(
        json.dumps(corpus_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    dataset_card_path.write_text(_build_dataset_card(corpus_manifest), encoding="utf-8")

    with tarfile.open(tar_path, "w:gz") as tar_file:
        tar_file.add(jsonl_path, arcname=jsonl_path.name)
        tar_file.add(normalized_jsonl_path, arcname=normalized_jsonl_path.name)
        tar_file.add(normalized_parquet_path, arcname=normalized_parquet_path.name)
        tar_file.add(corpus_manifest_path, arcname=corpus_manifest_path.name)
        tar_file.add(dataset_card_path, arcname=dataset_card_path.name)
        for path in legacy_json_files:
            tar_file.add(path, arcname=f"legacy/{path.relative_to(source_root)}")
        for path in normalized_jsonl_files:
            tar_file.add(path, arcname=f"normalized/{path.relative_to(normalized_root)}")
        for path in raw_files:
            tar_file.add(path, arcname=f"raw/{path.relative_to(raw_root)}")

    return BundleManifest(
        bundle_path=str(tar_path),
        sha256=_sha256(tar_path),
        file_count=len(legacy_json_files) + len(normalized_jsonl_files) + len(raw_files),
        uncompressed_bytes=uncompressed_bytes,
        normalized_record_count=normalized_record_count,
        raw_file_count=len(raw_files),
        manifest_path=str(corpus_manifest_path),
        dataset_card_path=str(dataset_card_path),
        normalized_jsonl_path=str(normalized_jsonl_path),
        normalized_parquet_path=str(normalized_parquet_path),
    )


def publish_to_zenodo(
    bundle: BundleManifest,
    token: str,
    endpoint: str,
    release_version: str = "",
    uploader: HttpUploader | None = None,
) -> dict[str, Any]:
    if uploader is None and hasattr(release_version, "upload_file"):
        uploader = release_version
        release_version = ""
    release_version = _resolve_release_version(release_version)
    metadata = {
        "title": "New Zealand Government Social Media Corpus/Archive",
        "upload_type": "dataset",
        "sha256": bundle.sha256,
        "file_count": bundle.file_count,
        "normalized_record_count": bundle.normalized_record_count,
        "release_version": release_version,
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


def publish_to_zenodo_deposition(
    bundle: BundleManifest,
    token: str,
    *,
    release_version: str = "",
    api_url: str = DEFAULT_ZENODO_DEPOSIT_API_URL,
    publish: bool = True,
    uploader: HttpUploader | None = None,
) -> dict[str, Any]:
    release_version = _resolve_release_version(release_version)
    metadata = {
        "metadata": {
            "title": "New Zealand Government Social Media Corpus/Archive",
            "upload_type": "dataset",
            "version": release_version,
            "access_right": "open",
            "license": "cc-zero",
            "keywords": [
                "corpus",
                "social media",
                "government",
                "New Zealand",
                "public records",
                "RSS",
                "Bluesky",
            ],
            "description": (
                "Normalized New Zealand government social media records, with RSS and "
                "adjacent public web source captures retained for discovery, provenance, "
                "and source-context evidence."
            ),
            "creators": [{"name": "sm-govt-nz maintainers"}],
        }
    }
    if uploader is not None:
        return uploader.upload_file(api_url, token, Path(bundle.bundle_path), metadata)
    try:
        import requests
    except ImportError:
        return UrlLibUploader().upload_file(api_url, token, Path(bundle.bundle_path), metadata)

    deposition = _zenodo_release_deposition(
        requests_module=requests,
        api_url=api_url,
        token=token,
        metadata=metadata,
    )
    deposition_id = deposition.get("id")
    bucket_url = deposition.get("links", {}).get("bucket")
    if not bucket_url:
        raise RuntimeError("Zenodo deposition response did not include an upload bucket URL.")
    uploaded = []
    for local_path in _zenodo_upload_paths(bundle):
        with Path(local_path).open("rb") as file:
            response = requests.put(
                f"{bucket_url}/{Path(local_path).name}",
                headers={"Authorization": f"Bearer {token}"},
                data=file,
                timeout=120,
            )
        response.raise_for_status()
        uploaded.append(response.json() if response.content else {"filename": Path(local_path).name})
    result = {
        "deposition_id": deposition_id,
        "deposition_url": deposition.get("links", {}).get("html") or deposition.get("links", {}).get("self"),
        "concept_record_id": deposition.get("conceptrecid"),
        "uploaded_files": uploaded,
        "submitted": False,
    }
    if publish:
        if not deposition_id:
            raise RuntimeError("Zenodo deposition response did not include a deposition id.")
        published = requests.post(
            f"{api_url.rstrip('/')}/{deposition_id}/actions/publish",
            headers={"Authorization": f"Bearer {token}"},
            timeout=120,
        )
        published.raise_for_status()
        published_deposition = published.json() if published.content else {}
        result.update(
            {
                "submitted": bool(published_deposition.get("submitted", True)),
                "state": published_deposition.get("state", "done"),
                "record_id": published_deposition.get("record_id"),
                "record_url": published_deposition.get("record_url"),
                "doi": published_deposition.get("doi"),
                "doi_url": published_deposition.get("doi_url"),
            }
        )
    return result


def _zenodo_release_deposition(
    *,
    requests_module: Any,
    api_url: str,
    token: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    version_record_id = _zenodo_latest_version_record_id(
        requests_module=requests_module,
        api_url=api_url,
        token=token,
    )
    if version_record_id:
        new_version = requests_module.post(
            f"{api_url.rstrip('/')}/{version_record_id}/actions/newversion",
            headers={"Authorization": f"Bearer {token}"},
            timeout=120,
        )
        new_version.raise_for_status()
        new_version_payload = new_version.json() if new_version.content else {}
        draft_url = (
            new_version_payload.get("links", {}).get("latest_draft")
            or new_version_payload.get("links", {}).get("draft")
        )
        if not draft_url:
            raise RuntimeError("Zenodo new version response did not include a draft URL.")
        draft = requests_module.get(
            draft_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=60,
        )
        draft.raise_for_status()
        draft_payload = draft.json()
        draft_id = draft_payload.get("id")
        if not draft_id:
            raise RuntimeError("Zenodo draft response did not include a deposition id.")
        updated = requests_module.put(
            f"{api_url.rstrip('/')}/{draft_id}",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            data=json.dumps(metadata),
            timeout=60,
        )
        updated.raise_for_status()
        return updated.json()

    created = requests_module.post(
        api_url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        data=json.dumps(metadata),
        timeout=60,
    )
    created.raise_for_status()
    return created.json()


def _zenodo_latest_version_record_id(
    *,
    requests_module: Any,
    api_url: str,
    token: str,
) -> str:
    version_record_id = os.getenv("ZENODO_VERSION_RECORD_ID", "").strip()
    if version_record_id:
        return version_record_id
    concept_record_id = os.getenv("ZENODO_CONCEPT_RECORD_ID", "").strip()
    if not concept_record_id:
        return ""
    records_api_url = _zenodo_records_api_url(api_url)
    latest = requests_module.get(
        f"{records_api_url.rstrip('/')}/{concept_record_id}/versions/latest",
        headers={"Authorization": f"Bearer {token}"},
        timeout=60,
    )
    latest.raise_for_status()
    latest_payload = latest.json()
    return str(latest_payload.get("id") or "")


def _zenodo_records_api_url(deposition_api_url: str) -> str:
    normalized = deposition_api_url.rstrip("/")
    if normalized.endswith("/deposit/depositions"):
        return normalized[: -len("/deposit/depositions")] + "/records"
    return "https://zenodo.org/api/records"


def publish_to_hugging_face(
    bundle: BundleManifest,
    token: str,
    repo_id: str,
    release_version: str = "",
    uploader: HttpUploader | None = None,
) -> dict[str, Any]:
    if uploader is None and hasattr(release_version, "upload_file"):
        uploader = release_version
        release_version = ""
    release_version = _resolve_release_version(release_version)
    endpoint = f"https://huggingface.co/api/datasets/{repo_id}/upload"
    metadata = {
        "repo_id": repo_id,
        "sha256": bundle.sha256,
        "file_count": bundle.file_count,
        "normalized_record_count": bundle.normalized_record_count,
        "release_version": release_version,
    }
    if uploader is not None:
        return uploader.upload_file(endpoint, token, Path(bundle.bundle_path), metadata)
    try:
        from huggingface_hub import HfApi
    except ImportError:
        return UrlLibUploader().upload_file(endpoint, token, Path(bundle.bundle_path), metadata)
    api = HfApi(token=token)
    api.create_repo(repo_id=repo_id, repo_type="dataset", exist_ok=True)
    uploaded_paths = []
    for local_path in _hugging_face_upload_paths(bundle):
        path_in_repo = _hugging_face_repo_path(local_path)
        api.upload_file(
            path_or_fileobj=str(local_path),
            path_in_repo=path_in_repo,
            repo_id=repo_id,
            repo_type="dataset",
        )
        uploaded_paths.append(path_in_repo)
    return {**metadata, "paths_in_repo": uploaded_paths}


def publish_to_osf(
    bundle: BundleManifest,
    token: str,
    upload_url: str,
    uploader: HttpUploader | None = None,
) -> dict[str, Any]:
    metadata = {
        "target": upload_url,
        "sha256": bundle.sha256,
        "file_count": bundle.file_count,
        "normalized_record_count": bundle.normalized_record_count,
    }
    if uploader is not None:
        return uploader.upload_file(upload_url, token, Path(bundle.bundle_path), metadata)
    try:
        import requests
    except ImportError:
        return UrlLibUploader().upload_file(upload_url, token, Path(bundle.bundle_path), metadata)
    uploaded_files = []
    for local_path in _osf_upload_paths(bundle):
        destination = _osf_file_upload_url(upload_url, local_path)
        with Path(local_path).open("rb") as file:
            response = requests.put(
                destination,
                headers={"Authorization": f"Bearer {token}"},
                data=file,
                timeout=120,
            )
        response.raise_for_status()
        uploaded_files.append(
            {
                "filename": Path(local_path).name,
                "url": destination,
                "response": response.json() if response.content else {},
            }
        )
    return {**metadata, "uploaded_files": uploaded_files}


def publish_from_env(
    bundle: BundleManifest,
    *,
    release_version: str = "",
    targets: set[str] | None = None,
) -> dict[str, Any]:
    requested_release_version = release_version
    release_version = _resolve_release_version(release_version)
    results: dict[str, Any] = {}
    active_targets = targets or {"huggingface", "zenodo"}
    if "zenodo" in active_targets:
        zenodo_token = os.getenv("ZENODO_TOKEN")
        zenodo_endpoint = os.getenv("ZENODO_DEPOSIT_ENDPOINT")
        if zenodo_token and zenodo_endpoint:
            results["zenodo"] = publish_to_zenodo(
                bundle,
                zenodo_token,
                zenodo_endpoint,
                release_version,
            )
        elif zenodo_token:
            results["zenodo"] = publish_to_zenodo_deposition(
                bundle,
                zenodo_token,
                release_version=release_version,
                api_url=os.getenv("ZENODO_DEPOSIT_API_URL", DEFAULT_ZENODO_DEPOSIT_API_URL),
                publish=_env_flag("ZENODO_PUBLISH", default=True),
            )
    osf_token = os.getenv("OSF_TOKEN")
    osf_upload_url = os.getenv("OSF_UPLOAD_URL", DEFAULT_OSF_UPLOAD_URL)
    if "osf" in active_targets and osf_token and osf_upload_url:
        results["osf"] = publish_to_osf(bundle, osf_token, osf_upload_url)
    hf_token = os.getenv("HF_TOKEN")
    if "huggingface" in active_targets and hf_token:
        hf_repo_id = os.getenv("HF_DATASET_REPO_ID") or _infer_hugging_face_repo_id(
            hf_token,
            os.getenv("HF_DATASET_NAME", DEFAULT_HF_DATASET_NAME),
        )
        if requested_release_version:
            results["huggingface"] = publish_to_hugging_face(
                bundle,
                hf_token,
                hf_repo_id,
                release_version,
            )
        else:
            results["huggingface"] = publish_to_hugging_face(bundle, hf_token, hf_repo_id)
    return results



def require_requested_publications(
    requested_targets: list[str],
    publication_results: dict[str, Any],
) -> None:
    missing = [target for target in requested_targets if target not in publication_results]
    if missing:
        raise RuntimeError(
            "Requested archive publication target(s) were not published: "
            + ", ".join(missing)
            + ". Check required secrets and repository configuration."
        )

def write_publication_status_report(
    *,
    bundle: BundleManifest,
    path: str | os.PathLike[str],
    mode: str,
    requested_targets: list[str],
    publication_results: dict[str, Any],
    release_version: str = "",
) -> None:
    release_version = _resolve_release_version(release_version)
    report = {
        "mode": mode,
        "release_version": release_version,
        "requested_targets": requested_targets,
        "source_git": _source_git_status(),
        "artifact": {
            "bundle_path": bundle.bundle_path,
            "sha256": bundle.sha256,
            "file_count": bundle.file_count,
            "normalized_record_count": bundle.normalized_record_count,
            "raw_file_count": bundle.raw_file_count,
        },
        "hugging_face": _publication_target_status(
            "huggingface",
            publication_results,
            default_repo_id=os.getenv("HF_DATASET_REPO_ID") or DEFAULT_HF_DATASET_REPO_ID,
        ),
        "zenodo": _publication_target_status(
            "zenodo",
            publication_results,
            default_repo_id=os.getenv("ZENODO_DEPOSIT_ENDPOINT")
            or os.getenv("ZENODO_DEPOSIT_API_URL")
            or DEFAULT_ZENODO_DEPOSIT_API_URL,
        ),
        "osf": _publication_target_status(
            "osf",
            publication_results,
            default_repo_id=os.getenv("OSF_UPLOAD_URL", DEFAULT_OSF_UPLOAD_URL),
        ),
    }
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _resolve_release_version(release_version: str) -> str:
    if not isinstance(release_version, str):
        return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-archive")
    normalized = (release_version or "").strip()
    if normalized:
        return normalized
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-archive")


def _source_git_status() -> dict[str, str]:
    head = _git_output(["rev-parse", "HEAD"])
    archive_commit = _git_output(
        [
            "log",
            "-1",
            "--format=%H",
            "--",
            "historical_archive",
            "historical_archive_normalized",
            "historical_archive_raw",
            "conductor/archive_state.json",
            "conductor/archive_source_health.json",
        ]
    )
    return {
        "head_sha": head,
        "latest_archive_commit_sha": archive_commit,
        "freshness_status": "fresh_at_source_head" if head and archive_commit else "unknown",
    }


def _git_output(args: list[str]) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return ""
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def _publication_target_status(
    key: str,
    publication_results: dict[str, Any],
    *,
    default_repo_id: str,
) -> dict[str, Any]:
    if key not in publication_results:
        return {
            "status": "not_requested_or_not_configured",
            "target": default_repo_id,
        }
    result = publication_results[key]
    return {
        "status": "published",
        "target": result.get("repo_id")
        or result.get("record_url")
        or result.get("doi_url")
        or result.get("deposition_url")
        or result.get("url")
        or default_repo_id,
        "result": result,
    }


def write_manifest(bundle: BundleManifest, path: str | os.PathLike[str]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(
        json.dumps(bundle.__dict__, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _env_flag(name: str, *, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _load_normalized_records(paths: list[Path]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in paths:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL in {path}:{line_number}") from exc
            if not isinstance(payload, dict):
                raise ValueError(
                    f"Normalized JSONL record must be an object in {path}:{line_number}"
                )
            records.append(payload)
    return records


def _build_corpus_manifest(
    *,
    legacy_json_files: list[Path],
    normalized_jsonl_files: list[Path],
    raw_files: list[Path],
    normalized_records: list[dict[str, Any]],
    jsonl_path: Path,
    normalized_jsonl_path: Path,
    normalized_parquet_path: Path,
    state_root: Path,
) -> dict[str, Any]:
    source_counts: dict[str, int] = {}
    date_ranges: dict[str, dict[str, str]] = {}
    for record in normalized_records:
        source = str(record.get("source_platform") or "unknown")
        source_counts[source] = source_counts.get(source, 0) + 1
        created_at = str(record.get("original_created_at") or "")
        if not created_at:
            continue
        current = date_ranges.setdefault(
            source, {"min_original_created_at": created_at, "max_original_created_at": created_at}
        )
        current["min_original_created_at"] = min(current["min_original_created_at"], created_at)
        current["max_original_created_at"] = max(current["max_original_created_at"], created_at)

    return {
        "title": "New Zealand Government Social Media Corpus/Archive",
        "canonical_name": "corpus-social-media-government-nz",
        "scope": "nz-government-social-media",
        "dataset_type": "corpus",
        "corpus_type": "social-media",
        "subject_scope": "government",
        "jurisdiction": "nz",
        "tags": [
            "corpus",
            "social-media",
            "government",
            "new-zealand",
            "region:nz",
            "public-records",
            "rss",
            "bluesky",
        ],
        "source_collections": [
            "courts-nz",
        ],
        "license": "Public source records; verify source-specific terms before redistribution.",
        "generated_artifacts": {
            jsonl_path.name: _artifact_summary(jsonl_path),
            normalized_jsonl_path.name: _artifact_summary(normalized_jsonl_path),
            normalized_parquet_path.name: _artifact_summary(normalized_parquet_path),
        },
        "source_counts": dict(sorted(source_counts.items())),
        "source_date_ranges": dict(sorted(date_ranges.items())),
        "record_index": _build_record_index(
            normalized_records,
            mirror_status=_load_mirror_status_by_record(state_root),
        ),
        "normalized_record_count": len(normalized_records),
        "normalized_shard_count": len(normalized_jsonl_files),
        "raw_file_count": len(raw_files),
        "legacy_json_file_count": len(legacy_json_files),
        "known_gaps": [
            "Platform capture beyond website, RSS, and Bluesky requires approved APIs, exports, or manual import workflows before automated archiving.",
            "Newsletter and email subscription ingress is pending source-specific mailbox/routing setup.",
            "Raw-source bundles are included in the Actions artifact and full archive tarball; separate gated raw publication can be added if source terms require it.",
        ],
        "provenance": (
            "Records are derived from New Zealand government social media and adjacent public "
            "source surfaces and preserve "
            "source platform, source account, source URL, capture timestamp, original timestamp, "
            "content hash, media references, raw path, and extraction method where available."
        ),
    }


def _artifact_summary(path: Path) -> dict[str, Any]:
    return {
        "path": path.name,
        "sha256": _sha256(path),
        "bytes": path.stat().st_size,
    }


def _build_record_index(
    normalized_records: list[dict[str, Any]],
    *,
    mirror_status: dict[str, list[dict[str, str]]],
) -> list[dict[str, Any]]:
    index: list[dict[str, Any]] = []
    for record in normalized_records:
        source_platform = str(record.get("source_platform") or "unknown")
        source_account = str(record.get("source_account") or "")
        source_record_id = str(record.get("record_id") or "")
        if not source_record_id:
            continue
        source_key = f"{source_platform}:{source_account}" if source_account else source_platform
        index.append(
            {
                "source_record_id": source_record_id,
                "source_platform": source_platform,
                "source_account": source_account,
                "source_key": source_key,
                "source_url": str(record.get("source_url") or record.get("canonical_url") or ""),
                "original_timestamp": str(record.get("original_created_at") or ""),
                "mirror_targets": mirror_status.get(
                    source_record_id,
                    _default_mirror_targets(source_platform),
                ),
            }
        )
    return sorted(index, key=lambda item: (item["original_timestamp"], item["source_record_id"]))


def _default_mirror_targets(source_platform: str) -> list[dict[str, str]]:
    if source_platform in {"bluesky", "x"}:
        return [{"target": "bluesky", "status": "pending", "mirror_url": ""}]
    return []


def _load_mirror_status_by_record(state_root: Path) -> dict[str, list[dict[str, str]]]:
    mirror_status: dict[str, list[dict[str, str]]] = {}
    _add_bluesky_backlog_status(
        mirror_status,
        state_root / "bluesky_backlog_state.json",
    )
    _add_archive_mirror_status(
        mirror_status,
        state_root / "archive_mirror_state.json",
    )
    return mirror_status


def _add_bluesky_backlog_status(
    mirror_status: dict[str, list[dict[str, str]]],
    state_path: Path,
) -> None:
    if not state_path.exists():
        return
    data = json.loads(state_path.read_text(encoding="utf-8"))
    for _source_account, record_ids in data.get("posted_post_ids", {}).items():
        if not isinstance(record_ids, list):
            continue
        for record_id in record_ids:
            mirror_status.setdefault(str(record_id), []).append(
                {
                    "target": "bluesky",
                    "status": "posted",
                    "mirror_url": "",
                }
            )


def _add_archive_mirror_status(
    mirror_status: dict[str, list[dict[str, str]]],
    state_path: Path,
) -> None:
    if not state_path.exists():
        return
    data = json.loads(state_path.read_text(encoding="utf-8"))
    detailed_by_target = data.get("posted_records", {})
    if isinstance(detailed_by_target, dict):
        for target, posted_by_source in detailed_by_target.items():
            if not isinstance(posted_by_source, dict):
                continue
            for _source_key, deliveries in posted_by_source.items():
                if not isinstance(deliveries, list):
                    continue
                for delivery in deliveries:
                    if not isinstance(delivery, dict):
                        continue
                    record_id = str(delivery.get("record_id") or "")
                    if not record_id:
                        continue
                    _append_mirror_status(
                        mirror_status,
                        record_id,
                        {
                            "target": str(delivery.get("target") or target),
                            "status": str(delivery.get("status") or "posted"),
                            "mirror_url": str(delivery.get("mirror_url") or ""),
                        },
                    )

    posted_by_target = data.get("posted_record_ids", {})
    if not isinstance(posted_by_target, dict):
        return
    for target, posted_by_source in posted_by_target.items():
        if not isinstance(posted_by_source, dict):
            continue
        for _source_key, record_ids in posted_by_source.items():
            if not isinstance(record_ids, list):
                continue
            for record_id in record_ids:
                _append_mirror_status(
                    mirror_status,
                    str(record_id),
                    {
                        "target": str(target),
                        "status": "posted",
                        "mirror_url": "",
                    },
                )


def _append_mirror_status(
    mirror_status: dict[str, list[dict[str, str]]],
    record_id: str,
    status: dict[str, str],
) -> None:
    statuses = mirror_status.setdefault(record_id, [])
    for existing in statuses:
        if existing.get("target") != status.get("target"):
            continue
        if not existing.get("mirror_url") and status.get("mirror_url"):
            existing.update(status)
        return
    statuses.append(status)


def _build_dataset_card(manifest: dict[str, Any]) -> str:
    source_lines = "\n".join(
        f"- {source}: {count} records" for source, count in manifest["source_counts"].items()
    )
    if not source_lines:
        source_lines = "- No normalized records were present when this bundle was generated."
    gap_lines = "\n".join(f"- {gap}" for gap in manifest["known_gaps"])
    return (
        "---\n"
        "license: other\n"
        "task_categories:\n"
        "- text-classification\n"
        "- text-generation\n"
        "language:\n"
        "- en\n"
        "pretty_name: New Zealand Government Social Media Corpus/Archive\n"
        "tags:\n"
        "- corpus\n"
        "- social-media\n"
        "- government\n"
        "- new-zealand\n"
        "- region:nz\n"
        "- public-records\n"
        "- rss\n"
        "- bluesky\n"
        "---\n\n"
        "# New Zealand Government Social Media Corpus/Archive\n\n"
        "Canonical name: `corpus-social-media-government-nz`.\n\n"
        "This dataset package contains normalized New Zealand government social media "
        "records, with RSS and adjacent public web source captures retained for "
        "discovery, provenance, and source-context evidence.\n\n"
        "## Contents\n\n"
        "- `normalized_archive.jsonl.gz`: combined normalized records from source/month shards.\n"
        "- `normalized_archive.parquet`: combined normalized records in Parquet format.\n"
        "- `normalized/`: source/month normalized JSONL shards.\n"
        "- `raw/`: raw source payloads captured before normalization.\n"
        "- `corpus_manifest.json`: checksums, coverage counts, date ranges, and known gaps.\n\n"
        "## Source Coverage\n\n"
        f"{source_lines}\n\n"
        "## Provenance\n\n"
        f"{manifest['provenance']}\n\n"
        "## Known Gaps\n\n"
        f"{gap_lines}\n"
    )


def _write_normalized_parquet(records: list[dict[str, Any]], path: Path) -> None:
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as error:
        raise RuntimeError("Install pyarrow to build normalized Parquet artifacts.") from error

    if records:
        rows = [_flatten_record_for_parquet(record) for record in records]
        field_names = sorted({field for row in rows for field in row})
        normalized_rows = [{field: row.get(field, "") for field in field_names} for row in rows]
        table = pa.Table.from_pylist(normalized_rows)
    else:
        table = pa.table({"record_id": pa.array([], type=pa.string())})
    pq.write_table(table, path)


def _flatten_record_for_parquet(record: dict[str, Any]) -> dict[str, str]:
    row: dict[str, str] = {}
    for key, value in record.items():
        if isinstance(value, (dict, list)):
            row[key] = json.dumps(value, ensure_ascii=False, sort_keys=True)
        elif value is None:
            row[key] = ""
        else:
            row[key] = str(value)
    return row


def _hugging_face_upload_paths(bundle: BundleManifest) -> list[Path]:
    candidates = [
        bundle.dataset_card_path,
        bundle.manifest_path,
        bundle.normalized_jsonl_path,
        bundle.normalized_parquet_path,
        bundle.bundle_path,
    ]
    return [Path(path) for path in candidates if path and Path(path).exists()]


def _hugging_face_repo_path(path: Path) -> str:
    if path.name == "README.md":
        return "README.md"
    if path.name.startswith("normalized_archive."):
        return f"data/{path.name}"
    if path.name == "corpus_manifest.json":
        return "metadata/corpus_manifest.json"
    return f"bundles/{path.name}"


def _infer_hugging_face_repo_id(token: str, dataset_name: str) -> str:
    try:
        from huggingface_hub import HfApi
    except ImportError as error:
        raise RuntimeError(
            "HF_DATASET_REPO_ID is required when huggingface_hub is not installed."
        ) from error
    api = HfApi(token=token)
    whoami = api.whoami(token=token)
    namespace = str(whoami.get("name") or "").strip()
    if not namespace:
        raise RuntimeError("Could not infer Hugging Face namespace from token.")
    return f"{namespace}/{dataset_name}"


def _zenodo_upload_paths(bundle: BundleManifest) -> list[Path]:
    candidates = [
        bundle.dataset_card_path,
        bundle.manifest_path,
        bundle.normalized_jsonl_path,
        bundle.normalized_parquet_path,
        bundle.bundle_path,
    ]
    return [Path(path) for path in candidates if path and Path(path).exists()]


def _osf_upload_paths(bundle: BundleManifest) -> list[Path]:
    candidates = [
        bundle.dataset_card_path,
        bundle.manifest_path,
        bundle.normalized_jsonl_path,
        bundle.normalized_parquet_path,
        bundle.bundle_path,
    ]
    return [Path(path) for path in candidates if path and Path(path).exists()]


def _osf_file_upload_url(upload_url: str, path: Path) -> str:
    separator = "" if upload_url.endswith("/") else "/"
    return f"{upload_url}{separator}{path.name}"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Bundle and optionally publish archives.")
    parser.add_argument("--archive-dir", default="historical_archive")
    parser.add_argument("--normalized-dir", default="historical_archive_normalized")
    parser.add_argument("--raw-dir", default="historical_archive_raw")
    parser.add_argument("--output-dir", default="dist")
    parser.add_argument("--manifest", default="dist/archive_manifest.json")
    parser.add_argument("--publish", action="store_true")
    parser.add_argument(
        "--publish-target",
        choices=["artifact", "huggingface", "zenodo", "osf", "all", "all_with_osf"],
        default="artifact",
    )
    parser.add_argument(
        "--status-report",
        default="dist/archive_publication_status.json",
    )
    parser.add_argument(
        "--release-version",
        default="",
        help="Archive release version. Defaults to a UTC timestamp.",
    )
    args = parser.parse_args()

    bundle = create_archive_bundle(
        args.archive_dir, args.output_dir, args.normalized_dir, args.raw_dir
    )
    write_manifest(bundle, args.manifest)
    release_version = _resolve_release_version(args.release_version)
    requested_targets = _requested_publish_targets(args.publish, args.publish_target)
    publication_results: dict[str, Any] = {}
    if requested_targets:
        publication_results = publish_from_env(
            bundle,
            release_version=release_version,
            targets=set(requested_targets),
        )
        print(json.dumps(publication_results, indent=2, sort_keys=True))
        require_requested_publications(requested_targets, publication_results)
    write_publication_status_report(
        bundle=bundle,
        path=args.status_report,
        mode="published" if requested_targets else "artifact_only",
        requested_targets=requested_targets,
        publication_results=publication_results,
        release_version=release_version,
    )


def _requested_publish_targets(publish: bool, publish_target: str) -> list[str]:
    if not publish and publish_target == "artifact":
        return []
    if publish_target == "artifact":
        return ["huggingface", "zenodo"] if publish else []
    if publish_target == "all":
        return ["huggingface", "zenodo"]
    if publish_target == "all_with_osf":
        return ["huggingface", "zenodo", "osf"]
    return [publish_target]


if __name__ == "__main__":
    main()
