import argparse
import json
import math
import os
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_SOURCE_TYPES = "rss,json_feed,bluesky,youtube,website_page,threads,facebook,instagram,linkedin,x"


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_source_types(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def source_matches(source: dict[str, Any], source_type: str) -> bool:
    return source.get("platform") == source_type or source.get("source_type") == source_type


def count_selected_sources(manifest: dict[str, Any], source_type: str) -> int:
    return sum(
        1
        for source in manifest.get("sources", [])
        if source_matches(source, source_type)
        and source.get("archive_status") in {"ready", "candidate"}
    )


def build_matrix(
    manifest: dict[str, Any],
    *,
    source_types: list[str],
    batch_size: int,
    max_batches: int,
) -> dict[str, Any]:
    include = []
    selected_counts = {}
    for source_type in source_types:
        selected_count = count_selected_sources(manifest, source_type)
        selected_counts[source_type] = selected_count
        if selected_count == 0:
            continue
        batch_count = max(1, math.ceil(selected_count / batch_size))
        if max_batches > 0:
            batch_count = min(batch_count, max_batches)
        for batch_index in range(batch_count):
            include.append(
                {
                    "source_type": source_type,
                    "batch_index": batch_index,
                    "batch_count": batch_count,
                    "offset": batch_index * batch_size,
                    "limit": batch_size,
                    "selected_count": selected_count,
                }
            )
    return {
        "include": include,
        "summary": {
            "batch_count": len(include),
            "batch_size": batch_size,
            "max_batches": max_batches,
            "selected_source_counts": dict(sorted(selected_counts.items())),
            "source_type_counts": dict(sorted(Counter(item["source_type"] for item in include).items())),
        },
    }


def write_github_output(key: str, value: str) -> None:
    output_path = os.getenv("GITHUB_OUTPUT")
    if output_path:
        with Path(output_path).open("a", encoding="utf-8") as handle:
            handle.write(f"{key}={value}\n")
    else:
        print(f"{key}={value}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build historical backlog shard matrix.")
    parser.add_argument("--manifest", type=Path, default=Path("conductor/govt_archive_source_manifest.json"))
    parser.add_argument("--source-types", default=DEFAULT_SOURCE_TYPES)
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--max-batches", type=int, default=0, help="0 means all batches")
    parser.add_argument("--output", type=Path, default=Path("conductor/historical_backlog_matrix.json"))
    parser.add_argument("--github-output-key", default="")
    args = parser.parse_args()

    if args.batch_size <= 0:
        raise ValueError("--batch-size must be positive")
    matrix = build_matrix(
        load_manifest(args.manifest),
        source_types=parse_source_types(args.source_types),
        batch_size=args.batch_size,
        max_batches=args.max_batches,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(matrix, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    matrix_json = json.dumps({"include": matrix["include"]}, separators=(",", ":"), sort_keys=True)
    if args.github_output_key:
        write_github_output(args.github_output_key, matrix_json)
        write_github_output("batch_count", str(matrix["summary"]["batch_count"]))
    print(f"Historical backlog matrix contains {matrix['summary']['batch_count']} batches.")


if __name__ == "__main__":
    main()
