#!/usr/bin/env python3
"""Check archive capture staleness against configured TTLs per source type.

Reads conductor/archive_state.json and flags any agency/source combination
where the last capture timestamp exceeds the configured TTL.

Usage:
    python scripts/check_archive_staleness.py
    python scripts/check_archive_staleness.py --state-path conductor/archive_state.json --health-path conductor/archive_source_health.json
"""

import json
import sys
import io
from datetime import datetime, timezone
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE_PATH = ROOT / "conductor" / "archive_state.json"
DEFAULT_HEALTH_PATH = ROOT / "conductor" / "archive_source_health.json"

# TTL in hours per source type (how old a capture can be before it's stale)
SOURCE_TTL_HOURS: dict[str, int] = {
    "rss": 24,          # Daily capture expected
    "bluesky": 6,       # Every-6-hour capture expected
    "website_page": 168,  # Weekly capture expected (7 days)
    "youtube": 168,      # Weekly capture expected (7 days)
    "website": 168,
}


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def check_staleness(
    state_path: Path = DEFAULT_STATE_PATH,
    health_path: Path = DEFAULT_HEALTH_PATH,
) -> dict:
    now = datetime.now(timezone.utc)
    state = load_json(state_path)
    health = load_json(health_path)

    stale_sources: list[dict] = []
    healthy_count = 0
    stale_count = 0
    unknown_count = 0

    # Check archive_state.json for per-agency per-source timestamps
    for agency_id, sources in state.items():
        if agency_id == "generated_at" or not isinstance(sources, dict):
            continue
        for source_type, capture_info in sources.items():
            if not isinstance(capture_info, dict):
                continue
            last_captured = capture_info.get("last_captured_at", "")
            if not last_captured:
                unknown_count += 1
                stale_sources.append({
                    "agency_id": agency_id,
                    "source_type": source_type,
                    "status": "unknown",
                    "last_captured_at": None,
                    "ttl_hours": SOURCE_TTL_HOURS.get(source_type, 24),
                    "message": "No capture timestamp recorded",
                })
                continue

            try:
                last_dt = datetime.fromisoformat(last_captured.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                unknown_count += 1
                continue

            ttl = SOURCE_TTL_HOURS.get(source_type, 24)
            hours_since = (now - last_dt).total_seconds() / 3600

            if hours_since > ttl:
                stale_count += 1
                stale_sources.append({
                    "agency_id": agency_id,
                    "source_type": source_type,
                    "status": "stale",
                    "last_captured_at": last_captured,
                    "hours_since_capture": round(hours_since, 1),
                    "ttl_hours": ttl,
                    "message": f"Stale: {round(hours_since, 1)}h since last capture (TTL: {ttl}h)",
                })
            else:
                healthy_count += 1

    # Also check archive_source_health.json for per-source health status
    for entry in health.get("results", []):
        agency_id = entry.get("agency_id", "unknown")
        source_type = entry.get("platform", "unknown")
        status = entry.get("status", "unknown")
        if status in ("unavailable", "degraded", "error"):
            stale_sources.append({
                "agency_id": agency_id,
                "source_type": source_type,
                "status": "degraded",
                "last_captured_at": entry.get("last_captured_at", ""),
                "message": f"Source degraded: {entry.get('reason', 'no reason given')}",
            })

    report = {
        "generated_at": now.isoformat(),
        "overall_status": "healthy" if stale_count == 0 else "stale_sources_detected",
        "summary": {
            "healthy_sources": healthy_count,
            "stale_sources": stale_count,
            "unknown_sources": unknown_count,
            "total_flagged": len(stale_sources),
        },
        "ttl_config": SOURCE_TTL_HOURS,
        "stale_sources": stale_sources,
    }

    print(f"Archive Staleness Check Report")
    print(f"  Generated: {report['generated_at']}")
    print(f"  Overall: {report['overall_status']}")
    print(f"  Healthy: {healthy_count}, Stale: {stale_count}, Unknown: {unknown_count}")
    if stale_sources:
        print(f"  Flagged sources:")
        for s in stale_sources:
            print(f"    [{s['status']}] {s['agency_id']}/{s['source_type']}: {s['message']}")

    return report


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Check archive capture staleness against TTLs")
    parser.add_argument("--state-path", type=Path, default=DEFAULT_STATE_PATH)
    parser.add_argument("--health-path", type=Path, default=DEFAULT_HEALTH_PATH)
    parser.add_argument("--report-path", type=Path, default=None,
                        help="Write report JSON to this path")
    args = parser.parse_args()

    report = check_staleness(
        state_path=args.state_path,
        health_path=args.health_path,
    )

    if args.report_path:
        write_json(args.report_path, report)

    # Exit code: 0 if healthy, 1 if any stale sources
    return 0 if report["overall_status"] == "healthy" else 1


if __name__ == "__main__":
    sys.exit(main())