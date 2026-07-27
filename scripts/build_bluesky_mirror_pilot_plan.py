"""Build the deterministic Bluesky mirror pilot onboarding plan."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any, Iterable, Mapping


def _values(value: object) -> set[str]:
    if isinstance(value, str):
        return {value} if value else set()
    if isinstance(value, list):
        return {str(item) for item in value if item}
    return set()


def _record_identity(record: Mapping[str, Any]) -> tuple[set[str], set[str]]:
    cross = record.get("cross_source_ids")
    cross = cross if isinstance(cross, Mapping) else {}
    source_ids = _values(cross.get("source_id")) | _values(cross.get("duplicate_source_ids"))
    urls = {
        str(record.get(key) or "").rstrip("/")
        for key in ("source_url", "canonical_url")
        if record.get(key)
    }
    return source_ids, urls


def iter_normalized_records(root: Path) -> Iterable[Mapping[str, Any]]:
    if not root.exists():
        return
    for path in sorted(root.rglob("*.jsonl")):
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_number}") from exc
            if isinstance(row, Mapping):
                yield row


def build_pilot_plan(
    registry: Mapping[str, Any],
    records: Iterable[Mapping[str, Any]],
    *,
    pilot_count: int = 2,
    generated_at: str = "",
) -> dict[str, Any]:
    record_index = []
    for record in records:
        source_ids, urls = _record_identity(record)
        record_index.append(
            (
                str(record.get("record_id") or ""),
                source_ids,
                urls,
                str(record.get("source_platform") or "unknown"),
            )
        )

    candidates = []
    for mirror in registry.get("mirrors", []):
        if not isinstance(mirror, Mapping):
            continue
        if mirror.get("lifecycle_state") != "candidate" or mirror.get("enabled"):
            continue
        if mirror.get("account_role") != "agency_mirror":
            continue
        source_ids = _values(mirror.get("source_ids"))
        source_urls = {url.rstrip("/") for url in _values(mirror.get("source_urls"))}
        matched_ids = set()
        platforms: Counter[str] = Counter()
        for record_id, record_source_ids, record_urls, platform in record_index:
            if (source_ids & record_source_ids) or (source_urls & record_urls):
                matched_ids.add(record_id)
                platforms[platform] += 1
        blockers = []
        if not mirror.get("issue_number"):
            blockers.append("onboarding_issue_missing")
        if not source_ids and not source_urls:
            blockers.append("registered_sources_missing")
        if not matched_ids:
            blockers.append("archived_records_missing")
        candidates.append(
            {
                "agency_id": str(mirror.get("agency_id") or ""),
                "agency_name": str(mirror.get("agency_name") or ""),
                "archive_record_count": len(matched_ids),
                "blockers": blockers,
                "eligible": not blockers,
                "environment": str(mirror.get("environment") or ""),
                "handle_candidates": list(mirror.get("handle_candidates") or []),
                "issue_number": mirror.get("issue_number"),
                "mirror_id": str(mirror.get("mirror_id") or ""),
                "platform_counts": dict(sorted(platforms.items())),
                "registered_source_count": len(source_ids or source_urls),
            }
        )

    eligible = sorted(
        (row for row in candidates if row["eligible"]),
        key=lambda row: (
            row["archive_record_count"],
            row["agency_id"],
            row["mirror_id"],
        ),
    )
    selected = eligible[: max(0, pilot_count)]
    selected_ids = {row["mirror_id"] for row in selected}
    for row in eligible:
        row["selected"] = row["mirror_id"] in selected_ids
    blocker_counts = Counter(blocker for row in candidates for blocker in row.get("blockers", []))
    return {
        "schema_version": 1,
        "generated_at": generated_at or datetime.now(UTC).isoformat(),
        "selection_policy": "smallest_archive_record_count_then_agency_id",
        "pilot_count": pilot_count,
        "selected": selected,
        "eligible_candidates": eligible,
        "blocker_counts": dict(sorted(blocker_counts.items())),
        "summary": {
            "candidate_count": len(candidates),
            "eligible_count": len(eligible),
            "selected_count": len(selected),
        },
    }


def render_markdown(plan: Mapping[str, Any]) -> str:
    lines = [
        "# Bluesky Mirror Pilot Plan",
        "",
        "Selection is deterministic: smallest matched archived backlog, then agency ID.",
        "No account, Environment, issue, credential, or post is created by this report.",
        "",
        "| Selected | Agency | Mirror ID | Records | Issue | Blockers |",
        "|---|---|---|---:|---:|---|",
    ]
    for row in plan.get("eligible_candidates", []):
        lines.append(
            "| {selected} | {agency} | `{mirror}` | {records} | {issue} | {blockers} |".format(
                selected="yes" if row.get("selected") else "",
                agency=row.get("agency_name") or row.get("agency_id"),
                mirror=row.get("mirror_id"),
                records=row.get("archive_record_count", 0),
                issue=row.get("issue_number") or "",
                blockers=", ".join(row.get("blockers", [])),
            )
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=Path("config/mirror_accounts.json"))
    parser.add_argument(
        "--normalized-root", type=Path, default=Path("historical_archive_normalized")
    )
    parser.add_argument(
        "--output", type=Path, default=Path("conductor/bluesky_mirror_pilot_plan.json")
    )
    parser.add_argument(
        "--summary", type=Path, default=Path("conductor/bluesky_mirror_pilot_plan.md")
    )
    parser.add_argument("--pilot-count", type=int, default=2)
    args = parser.parse_args()
    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    plan = build_pilot_plan(
        registry,
        iter_normalized_records(args.normalized_root),
        pilot_count=args.pilot_count,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.summary.write_text(render_markdown(plan), encoding="utf-8")
    print(json.dumps(plan["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
