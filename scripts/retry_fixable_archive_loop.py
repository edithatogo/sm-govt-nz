import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
GAP_MAP = ROOT / "conductor" / "archive_gap_map.json"
COMPLETION_MATRIX = ROOT / "conductor" / "archive_completion_matrix.json"

RETRYABLE_BLOCKERS = {
    "api": {
        "heuristic_endpoint_public_access_blocked",
        "heuristic_endpoint_invalid",
        "heuristic_endpoint_exhausted_public_retries",
    },
    "json_feed": {
        "heuristic_endpoint_public_access_blocked",
        "heuristic_endpoint_invalid",
        "heuristic_endpoint_exhausted_public_retries",
    },
    "linkedin": {"linkedin_public_access_rate_limited"},
    "website_page": {
        "heuristic_endpoint_public_access_blocked",
        "website_exhausted_http_and_browser_fallbacks",
    },
}
SOURCE_TYPE_TO_PLATFORM = {"api_endpoint": "api"}


def run_command(args: list[str]) -> None:
    completed = subprocess.run(args, cwd=ROOT, check=False, text=True)
    if completed.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(args)}")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def stable_shard(source_id: str, shard_count: int) -> int:
    digest = hashlib.sha256(source_id.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % shard_count


def retryable_source_ids(
    matrix: dict[str, Any],
    source_type: str,
    *,
    shard_index: int,
    shard_count: int,
    limit: int,
) -> list[str]:
    platform = SOURCE_TYPE_TO_PLATFORM.get(source_type, source_type)
    blockers = RETRYABLE_BLOCKERS.get(platform, set())
    source_ids = sorted(
        str(row.get("source_id"))
        for row in matrix.get("sources", [])
        if row.get("source_id")
        and platform in {str(row.get("platform") or ""), str(row.get("source_type") or "")}
        and str(row.get("blocker_class") or "") in blockers
        and stable_shard(str(row.get("source_id")), shard_count) == shard_index
    )
    return source_ids[:limit] if limit > 0 else source_ids


def archive_retry_shard(
    source_type: str,
    source_ids: list[str],
    *,
    fetch_timeout: int,
    per_source_delay: float,
    retry_attempts: int,
    retry_backoff: float,
) -> None:
    if not source_ids:
        print(f"  No retryable {source_type} sources in this shard.")
        return
    report_slug = source_type.replace("_endpoint", "")
    run_command(
        [
            sys.executable,
            "scripts/archive_registered_sources.py",
            "--source-type",
            source_type,
            "--include-blocked",
            "--source-ids",
            ",".join(source_ids),
            "--fetch-timeout",
            str(fetch_timeout),
            "--per-source-delay",
            str(per_source_delay),
            "--retry-attempts",
            str(retry_attempts),
            "--retry-backoff",
            str(retry_backoff),
            "--report",
            f"conductor/{report_slug}_archive_paced_retry_report.json",
            "--summary",
            f"conductor/{report_slug}_archive_paced_retry_summary.md",
        ]
    )


def discover_public_newsletter_archives(max_agencies: int) -> None:
    run_command(
        [
            sys.executable,
            "scripts/discover_govt_source_candidates.py",
            "--probe-homepages",
            "--max-agencies",
            str(max_agencies),
        ]
    )
    run_command(
        [
            sys.executable,
            "scripts/promote_govt_source_candidates.py",
            "--report",
            "conductor/govt_source_candidate_report.json",
            "--manifest",
            "conductor/govt_archive_source_manifest.json",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run paced, deterministic retries for public archive sources.")
    parser.add_argument("--max-iterations", type=int, default=1)
    parser.add_argument("--source-types", default="api_endpoint,json_feed,website_page,linkedin")
    parser.add_argument("--source-limit", type=int, default=5)
    parser.add_argument("--shard-count", type=int, default=16)
    parser.add_argument("--shard-index", type=int, default=-1)
    parser.add_argument("--fetch-timeout", type=int, default=12)
    parser.add_argument("--per-source-delay", type=float, default=3.0)
    parser.add_argument("--retry-attempts", type=int, default=2)
    parser.add_argument("--retry-backoff", type=float, default=2.0)
    parser.add_argument("--discover-newsletters", action="store_true")
    parser.add_argument("--newsletter-max-agencies", type=int, default=0)
    args = parser.parse_args()

    source_types = [part.strip() for part in args.source_types.split(",") if part.strip()]
    if not source_types:
        raise SystemExit("No source types supplied.")
    shard_count = max(1, args.shard_count)
    run_number = int(os.getenv("GITHUB_RUN_NUMBER", "0") or 0)
    shard_index = args.shard_index if args.shard_index >= 0 else run_number % shard_count
    if shard_index >= shard_count:
        raise SystemExit("shard_index must be lower than shard_count")

    if args.discover_newsletters:
        print("Discovering public newsletter archives...")
        discover_public_newsletter_archives(max(0, args.newsletter_max_agencies))

    for iteration in range(1, max(1, args.max_iterations) + 1):
        print(f"Iteration {iteration}/{max(1, args.max_iterations)}; shard={shard_index}/{shard_count}")
        matrix = load_json(COMPLETION_MATRIX)
        attempted = 0
        for source_type in source_types:
            source_ids = retryable_source_ids(
                matrix,
                source_type,
                shard_index=shard_index,
                shard_count=shard_count,
                limit=max(0, args.source_limit),
            )
            attempted += len(source_ids)
            print(f"  Retrying {len(source_ids)} {source_type} sources...")
            archive_retry_shard(
                source_type,
                source_ids,
                fetch_timeout=max(1, args.fetch_timeout),
                per_source_delay=max(0.0, args.per_source_delay),
                retry_attempts=max(1, args.retry_attempts),
                retry_backoff=max(0.0, args.retry_backoff),
            )
        run_command([sys.executable, "scripts/build_archive_gap_map.py"])
        run_command([sys.executable, "scripts/build_archive_completion_matrix.py"])
        if attempted == 0:
            print("Stop condition reached: this deterministic shard has no retryable sources.")
            break


if __name__ == "__main__":
    main()
