import argparse
import hashlib
import json
import os
import shutil
import tarfile
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


LFS_HEADER = "version https://git-lfs.github.com/spec/v1"
DEFAULT_REPO_ID = "edithatogo/corpus-social-media-government-nz"
DEFAULT_BUNDLE_PATH = "bundles/historical_archive.tar.gz"
DEFAULT_MANIFEST = Path("conductor/huggingface_lfs_migration_manifest.json")
DEFAULT_ROLLOVER_THRESHOLD_MB = 50


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_lfs_pointer(path: Path) -> dict[str, Any] | None:
    if not path.is_file() or path.stat().st_size > 1024:
        return None
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0] != LFS_HEADER:
        return None
    values = dict(line.split(" ", 1) for line in lines[1:] if " " in line)
    oid = values.get("oid", "")
    if not oid.startswith("sha256:") or not values.get("size", "").isdigit():
        raise ValueError(f"Invalid Git LFS pointer: {path}")
    return {"oid": oid.removeprefix("sha256:"), "size": int(values["size"])}


def discover_lfs_pointers(normalized_root: Path) -> list[dict[str, Any]]:
    pointers = []
    for path in sorted(normalized_root.rglob("*")):
        pointer = parse_lfs_pointer(path)
        if pointer:
            pointers.append({"path": path.as_posix(), **pointer})
    return pointers


def default_download(repo_id: str, path_in_repo: str, token: str | None) -> Path:
    from huggingface_hub import hf_hub_download

    return Path(
        hf_hub_download(
            repo_id=repo_id,
            filename=path_in_repo,
            repo_type="dataset",
            token=token or None,
        )
    )


def _extract_verified_payloads(
    bundle_path: Path,
    pointers: list[dict[str, Any]],
    normalized_root: Path,
    output_root: Path,
) -> list[dict[str, Any]]:
    migrated = []
    with tarfile.open(bundle_path, "r:gz") as archive:
        for pointer in pointers:
            source_path = Path(pointer["path"])
            relative_path = source_path.relative_to(normalized_root)
            member_name = f"normalized/{relative_path.as_posix()}"
            try:
                member = archive.getmember(member_name)
            except KeyError as exc:
                raise RuntimeError(f"Published Hugging Face bundle is missing {member_name}") from exc
            if not member.isfile():
                raise RuntimeError(f"Published bundle member is not a regular file: {member_name}")
            extracted = archive.extractfile(member)
            if extracted is None:
                raise RuntimeError(f"Could not read published bundle member: {member_name}")
            destination = output_root / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("wb") as output:
                shutil.copyfileobj(extracted, output)
            actual_size = destination.stat().st_size
            actual_sha256 = sha256_file(destination)
            if actual_size != pointer["size"] or actual_sha256 != pointer["oid"]:
                raise RuntimeError(
                    f"Published bundle payload mismatch for {pointer['path']}: "
                    f"expected {pointer['size']} bytes/{pointer['oid']}, "
                    f"got {actual_size} bytes/{actual_sha256}"
                )
            migrated.append(
                {
                    **pointer,
                    "relative_path": relative_path.as_posix(),
                    "verified_sha256": actual_sha256,
                    "verified_size": actual_size,
                }
            )
    return migrated


def _remove_lfs_tracking(attributes_path: Path) -> None:
    retained = []
    if attributes_path.is_file():
        retained = [
            line
            for line in attributes_path.read_text(encoding="utf-8").splitlines()
            if not ("filter=lfs" in line and "historical_archive_normalized/website" in line)
        ]
    if not retained:
        retained = ["# Large archive baselines are stored in the Hugging Face dataset."]
    attributes_path.write_text("\n".join(retained) + "\n", encoding="utf-8")


def migrate_lfs_payloads(
    *,
    repo_id: str,
    bundle_path_in_repo: str,
    normalized_root: Path,
    manifest_path: Path,
    destination_prefix: str,
    token: str,
    cleanup: bool,
    attributes_path: Path = Path(".gitattributes"),
    download: Callable[[str, str, str | None], Path] = default_download,
    api: Any | None = None,
    local_bundle: Path | None = None,
    source_description: str = "",
) -> dict[str, Any]:
    pointers = discover_lfs_pointers(normalized_root)
    if not pointers:
        if manifest_path.is_file():
            return json.loads(manifest_path.read_text(encoding="utf-8"))
        raise RuntimeError("No Git LFS pointers were found and no prior migration manifest exists.")
    if not token:
        raise RuntimeError("HF_TOKEN is required for Git LFS migration.")

    bundle_path = local_bundle or download(repo_id, bundle_path_in_repo, token)
    if not bundle_path.is_file():
        raise RuntimeError(f"Migration source bundle does not exist: {bundle_path}")
    with tempfile.TemporaryDirectory(prefix="sm-govt-nz-lfs-") as temporary_directory:
        temporary_root = Path(temporary_directory)
        extracted_root = temporary_root / "extracted"
        entries = _extract_verified_payloads(
            bundle_path,
            pointers,
            normalized_root,
            extracted_root,
        )
        for entry in entries:
            entry["hf_path"] = (
                f"{destination_prefix.rstrip('/')}/{normalized_root.as_posix()}/"
                f"{entry['relative_path']}"
            )
        manifest = {
            "schema_version": 1,
            "migrated_at": datetime.now(UTC).isoformat(),
            "dataset_repo_id": repo_id,
            "source_bundle_path": bundle_path_in_repo,
            "source_description": source_description or f"huggingface:{repo_id}/{bundle_path_in_repo}",
            "source_bundle_sha256": sha256_file(bundle_path),
            "destination_prefix": destination_prefix,
            "entries": entries,
        }
        temporary_manifest = temporary_root / "git_lfs_migration_manifest.json"
        temporary_manifest.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        if api is None:
            from huggingface_hub import HfApi

            api = HfApi(token=token)
        api.create_repo(repo_id=repo_id, repo_type="dataset", exist_ok=True)
        for entry in entries:
            api.upload_file(
                path_or_fileobj=str(extracted_root / entry["relative_path"]),
                path_in_repo=entry["hf_path"],
                repo_id=repo_id,
                repo_type="dataset",
                commit_message="Migrate Git LFS archive baseline",
            )
        api.upload_file(
            path_or_fileobj=str(temporary_manifest),
            path_in_repo="metadata/git_lfs_migration_manifest.json",
            repo_id=repo_id,
            repo_type="dataset",
            commit_message="Record Git LFS archive migration",
        )

        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(temporary_manifest, manifest_path)

    if cleanup:
        for pointer in pointers:
            Path(pointer["path"]).unlink()
        _remove_lfs_tracking(attributes_path)
    return manifest


def _record_key(line: bytes) -> str:
    try:
        payload = json.loads(line)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return hashlib.sha256(line).hexdigest()
    return str(payload.get("record_id") or payload.get("id") or hashlib.sha256(line).hexdigest())


def merge_jsonl(baseline: Path, delta: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    with temporary.open("wb") as output:
        for source in (baseline, delta):
            if not source.is_file():
                continue
            with source.open("rb") as input_file:
                for line in input_file:
                    if not line.strip():
                        continue
                    key = _record_key(line)
                    if key in seen:
                        continue
                    seen.add(key)
                    output.write(line.rstrip(b"\r\n") + b"\n")
    temporary.replace(destination)


def rollover_large_deltas(
    *,
    repo_id: str,
    normalized_root: Path,
    manifest_path: Path,
    destination_prefix: str,
    threshold_bytes: int,
    token: str,
    cleanup: bool,
    download: Callable[[str, str, str | None], Path] = default_download,
    api: Any | None = None,
) -> dict[str, Any]:
    candidates = [
        path
        for path in sorted(normalized_root.rglob("*.jsonl"))
        if path.is_file()
        and not parse_lfs_pointer(path)
        and path.stat().st_size >= threshold_bytes
    ]
    if not candidates:
        return {
            "status": "no_rollover_needed",
            "threshold_bytes": threshold_bytes,
            "rollover_count": 0,
        }
    if not token:
        raise RuntimeError("HF_TOKEN is required when archive deltas need rollover.")

    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        manifest = {
            "schema_version": 1,
            "dataset_repo_id": repo_id,
            "destination_prefix": destination_prefix,
            "entries": [],
        }
    if str(manifest.get("dataset_repo_id", repo_id)) != repo_id:
        raise RuntimeError("Rollover repository does not match the migration manifest.")

    existing_entries = {
        str(entry["relative_path"]): entry
        for entry in manifest.get("entries", [])
        if entry.get("relative_path")
    }
    if api is None:
        from huggingface_hub import HfApi

        api = HfApi(token=token)
    api.create_repo(repo_id=repo_id, repo_type="dataset", exist_ok=True)

    rolled_over = []
    with tempfile.TemporaryDirectory(prefix="sm-govt-nz-rollover-") as temporary_directory:
        temporary_root = Path(temporary_directory)
        for delta in candidates:
            relative_path = delta.relative_to(normalized_root).as_posix()
            hf_path = (
                f"{destination_prefix.rstrip('/')}/{normalized_root.as_posix()}/"
                f"{relative_path}"
            )
            merged = temporary_root / relative_path
            existing = existing_entries.get(relative_path)
            if existing:
                baseline = download(repo_id, str(existing["hf_path"]), token)
                expected_size = int(existing["size"])
                expected_sha256 = str(existing["oid"])
                if baseline.stat().st_size != expected_size or sha256_file(baseline) != expected_sha256:
                    raise RuntimeError(
                        f"Hugging Face baseline failed verification before rollover: {existing['hf_path']}"
                    )
                merge_jsonl(baseline, delta, merged)
            else:
                merged.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(delta, merged)

            entry = {
                **(existing or {}),
                "path": delta.as_posix(),
                "relative_path": relative_path,
                "hf_path": hf_path,
                "oid": sha256_file(merged),
                "size": merged.stat().st_size,
                "verified_sha256": sha256_file(merged),
                "verified_size": merged.stat().st_size,
                "rolled_over_at": datetime.now(UTC).isoformat(),
            }
            api.upload_file(
                path_or_fileobj=str(merged),
                path_in_repo=hf_path,
                repo_id=repo_id,
                repo_type="dataset",
                commit_message="Rollover normalized archive delta",
            )
            existing_entries[relative_path] = entry
            rolled_over.append(entry)

        manifest.update(
            {
                "schema_version": 1,
                "dataset_repo_id": repo_id,
                "destination_prefix": destination_prefix,
                "last_rollover_at": datetime.now(UTC).isoformat(),
                "entries": [existing_entries[key] for key in sorted(existing_entries)],
            }
        )
        temporary_manifest = temporary_root / "git_lfs_migration_manifest.json"
        temporary_manifest.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        api.upload_file(
            path_or_fileobj=str(temporary_manifest),
            path_in_repo="metadata/git_lfs_migration_manifest.json",
            repo_id=repo_id,
            repo_type="dataset",
            commit_message="Record normalized archive rollover",
        )
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(temporary_manifest, manifest_path)

    if cleanup:
        for path in candidates:
            path.unlink()
    return {
        "status": "rolled_over",
        "threshold_bytes": threshold_bytes,
        "rollover_count": len(rolled_over),
        "entries": rolled_over,
    }


def hydrate_archive(
    *,
    manifest_path: Path,
    source_root: Path,
    output_root: Path,
    token: str | None,
    download: Callable[[str, str, str | None], Path] = default_download,
) -> dict[str, Any]:
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    copied = 0
    skipped_pointers = 0
    if source_root.is_dir():
        for source in sorted(source_root.rglob("*")):
            if not source.is_file():
                continue
            if parse_lfs_pointer(source):
                skipped_pointers += 1
                continue
            destination = output_root / source.relative_to(source_root)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            copied += 1

    if not manifest_path.is_file():
        return {
            "status": "migration_manifest_missing",
            "copied_files": copied,
            "skipped_lfs_pointers": skipped_pointers,
            "hydrated_files": 0,
        }

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    repo_id = str(manifest["dataset_repo_id"])
    hydrated = 0
    for entry in manifest.get("entries", []):
        baseline = download(repo_id, str(entry["hf_path"]), token)
        if baseline.stat().st_size != int(entry["size"]) or sha256_file(baseline) != entry["oid"]:
            raise RuntimeError(f"Hugging Face migrated payload failed verification: {entry['hf_path']}")
        relative_path = Path(str(entry["relative_path"]))
        destination = output_root / relative_path
        delta = destination if destination.is_file() else Path("__missing_delta__")
        merge_jsonl(baseline, delta, destination)
        hydrated += 1
    return {
        "status": "hydrated",
        "copied_files": copied,
        "skipped_lfs_pointers": skipped_pointers,
        "hydrated_files": hydrated,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate Git LFS archive payloads to Hugging Face.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    migrate = subparsers.add_parser("migrate")
    migrate.add_argument("--repo-id", default=DEFAULT_REPO_ID)
    migrate.add_argument("--bundle-path", default=DEFAULT_BUNDLE_PATH)
    migrate.add_argument("--normalized-root", type=Path, default=Path("historical_archive_normalized"))
    migrate.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    migrate.add_argument("--destination-prefix", default="archive")
    migrate.add_argument("--local-bundle", type=Path)
    migrate.add_argument("--source-description", default="")
    migrate.add_argument("--cleanup", action="store_true")

    hydrate = subparsers.add_parser("hydrate")
    hydrate.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    hydrate.add_argument("--source-root", type=Path, default=Path("historical_archive_normalized"))
    hydrate.add_argument("--output-root", type=Path, default=Path("dist/hydrated_archive_normalized"))

    rollover = subparsers.add_parser("rollover")
    rollover.add_argument("--repo-id", default=DEFAULT_REPO_ID)
    rollover.add_argument("--normalized-root", type=Path, default=Path("historical_archive_normalized"))
    rollover.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    rollover.add_argument("--destination-prefix", default="archive")
    rollover.add_argument("--threshold-mb", type=int, default=DEFAULT_ROLLOVER_THRESHOLD_MB)
    rollover.add_argument("--cleanup", action="store_true")

    args = parser.parse_args()
    if args.command == "migrate":
        result = migrate_lfs_payloads(
            repo_id=args.repo_id,
            bundle_path_in_repo=args.bundle_path,
            normalized_root=args.normalized_root,
            manifest_path=args.manifest,
            destination_prefix=args.destination_prefix,
            token=os.getenv("HF_TOKEN", ""),
            cleanup=args.cleanup,
            local_bundle=args.local_bundle,
            source_description=args.source_description,
        )
    elif args.command == "hydrate":
        result = hydrate_archive(
            manifest_path=args.manifest,
            source_root=args.source_root,
            output_root=args.output_root,
            token=os.getenv("HF_TOKEN") or None,
        )
    else:
        result = rollover_large_deltas(
            repo_id=args.repo_id,
            normalized_root=args.normalized_root,
            manifest_path=args.manifest,
            destination_prefix=args.destination_prefix,
            threshold_bytes=args.threshold_mb * 1024 * 1024,
            token=os.getenv("HF_TOKEN", ""),
            cleanup=args.cleanup,
        )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
