import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def build_compaction_manifest(
    *,
    normalized_dir: str | Path = "historical_archive_normalized",
    raw_dir: str | Path = "historical_archive_raw",
    generated_at: str | None = None,
) -> dict[str, Any]:
    normalized_root = Path(normalized_dir)
    raw_root = Path(raw_dir)
    generated_timestamp = generated_at or datetime.now(UTC).replace(microsecond=0).isoformat()

    normalized_shards = _normalized_shards(normalized_root)
    raw_shards = _raw_shards(raw_root)

    return {
        "generated_at": generated_timestamp,
        "policy": {
            "mode": "monthly_manifest",
            "description": (
                "Git keeps source/month archive shards and this lightweight manifest. "
                "Compaction records checksums and counts without deleting or rewriting raw evidence."
            ),
            "raw_retention": "append_only",
            "normalized_retention": "append_only",
        },
        "normalized": normalized_shards,
        "raw": raw_shards,
        "totals": {
            "normalized_record_count": sum(item["record_count"] for item in normalized_shards),
            "normalized_shard_count": len(normalized_shards),
            "normalized_bytes": sum(item["bytes"] for item in normalized_shards),
            "raw_file_count": sum(item["file_count"] for item in raw_shards),
            "raw_shard_count": len(raw_shards),
            "raw_bytes": sum(item["bytes"] for item in raw_shards),
        },
    }


def write_compaction_manifest(manifest: dict[str, Any], output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _normalized_shards(root: Path) -> list[dict[str, Any]]:
    shards: list[dict[str, Any]] = []
    if not root.exists():
        return shards
    for path in sorted(item for item in root.glob("*/*.jsonl") if item.is_file()):
        source = path.parent.name
        month = path.stem
        shards.append(
            {
                "source": source,
                "month": month,
                "path": _posix(path),
                "record_count": _jsonl_record_count(path),
                "bytes": path.stat().st_size,
                "sha256": _file_sha256(path),
            }
        )
    return shards


def _raw_shards(root: Path) -> list[dict[str, Any]]:
    shards: list[dict[str, Any]] = []
    if not root.exists():
        return shards
    for source_dir in sorted(item for item in root.iterdir() if item.is_dir()):
        for month_dir in sorted(item for item in source_dir.iterdir() if item.is_dir()):
            files = sorted(item for item in month_dir.rglob("*") if item.is_file())
            shards.append(
                {
                    "source": source_dir.name,
                    "month": month_dir.name,
                    "path": _posix(month_dir),
                    "file_count": len(files),
                    "bytes": sum(item.stat().st_size for item in files),
                    "digest_mode": "path_size_inventory",
                    "sha256": _directory_digest(month_dir, files),
                }
            )
    return shards


def _directory_digest(root: Path, files: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in files:
        stat = path.stat()
        digest.update(_posix(path.relative_to(root)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(stat.st_size).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def _jsonl_record_count(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _posix(path: str | Path) -> str:
    return Path(path).as_posix()


def main() -> None:
    parser = argparse.ArgumentParser(description="Build archive compaction manifest.")
    parser.add_argument("--normalized-dir", default="historical_archive_normalized")
    parser.add_argument("--raw-dir", default="historical_archive_raw")
    parser.add_argument("--output", default="conductor/archive_compaction_manifest.json")
    args = parser.parse_args()

    manifest = build_compaction_manifest(
        normalized_dir=args.normalized_dir,
        raw_dir=args.raw_dir,
    )
    write_compaction_manifest(manifest, args.output)


if __name__ == "__main__":
    main()
