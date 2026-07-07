import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_MANIFEST = Path("conductor/govt_archive_source_manifest.json")
DEFAULT_POLICY = Path("config/manual_seed_onboarding.json")
DEFAULT_REPORT = Path("conductor/manual_seed_onboarding_report.json")
DEFAULT_SUMMARY = Path("conductor/manual_seed_onboarding_summary.md")
DEFAULT_QUEUE = Path("conductor/manual_seed_work_queue.json")
DEFAULT_NEXT_BATCH_TEMPLATES = Path("conductor/manual_seed_next_batch_templates.json")
DEFAULT_DROP_TARGETS = Path("conductor/manual_seed_drop_targets.md")
DEFAULT_MANUAL_SEED_ROOT = Path("manual_archive_seeds")
DEFAULT_PLATFORMS = ["facebook", "instagram", "threads", "linkedin", "x", "newsletter"]
PLATFORM_PRIORITY = {
    "threads": 10,
    "newsletter": 20,
    "linkedin": 30,
    "facebook": 40,
    "instagram": 50,
    "x": 60,
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def seed_candidates(source: dict[str, Any], policy: dict[str, Any], seed_root: Path) -> list[str]:
    platform = str(source.get("platform") or "")
    source_id = str(source.get("source_id") or "")
    agency_id = str(source.get("agency_id") or "")
    seed_directory = str(policy.get("seed_directory") or seed_root / platform).replace("\\", "/")
    return [
        f"{seed_directory}/{source_id}.json" if source_id else "",
        f"{seed_directory}/{agency_id}.json" if agency_id else "",
    ]


def seed_present(candidates: list[str]) -> bool:
    return any(candidate and Path(candidate).is_file() for candidate in candidates)


def onboarding_item(source: dict[str, Any], policy: dict[str, Any], seed_root: Path) -> dict[str, Any]:
    candidates = [candidate for candidate in seed_candidates(source, policy, seed_root) if candidate]
    present = seed_present(candidates)
    platform = str(source.get("platform") or "")
    if present:
        onboarding_status = "seed_present"
    elif platform == "linkedin":
        onboarding_status = "public_fallback_available"
    else:
        onboarding_status = "needs_authorized_seed_or_api"
    return {
        "source_id": source.get("source_id", ""),
        "agency_id": source.get("agency_id", ""),
        "agency_name": source.get("agency_name", ""),
        "platform": platform,
        "source_type": source.get("source_type", ""),
        "url": source.get("url", ""),
        "account": source.get("account", ""),
        "archive_status": source.get("archive_status", ""),
        "feasibility": source.get("feasibility", ""),
        "onboarding_status": onboarding_status,
        "acceptable_access_methods": policy.get("acceptable_access_methods", []),
        "required_authorization": policy.get("required_authorization", ""),
        "seed_candidates": candidates,
        "preferred_seed_path": candidates[0] if candidates else "",
        "seed_schema": policy.get("seed_schema", ""),
        "live_capture_policy": policy.get("live_capture_policy", ""),
    }


def work_queue_item(item: dict[str, Any]) -> dict[str, Any]:
    platform = str(item.get("platform") or "")
    return {
        "source_id": item.get("source_id", ""),
        "agency_id": item.get("agency_id", ""),
        "agency_name": item.get("agency_name", ""),
        "platform": platform,
        "url": item.get("url", ""),
        "account": item.get("account", ""),
        "onboarding_status": item.get("onboarding_status", ""),
        "preferred_seed_path": item.get("preferred_seed_path", ""),
        "seed_candidates": item.get("seed_candidates", []),
        "required_authorization": item.get("required_authorization", ""),
        "acceptable_access_methods": item.get("acceptable_access_methods", []),
        "priority_rank": PLATFORM_PRIORITY.get(platform, 999),
    }


def build_work_queue(report: dict[str, Any]) -> dict[str, Any]:
    queue_items = [
        work_queue_item(item)
        for item in report.get("items", [])
        if item.get("onboarding_status") == "needs_authorized_seed_or_api"
    ]
    queue_items.sort(
        key=lambda item: (
            item["priority_rank"],
            str(item.get("agency_name") or ""),
            str(item.get("agency_id") or ""),
            str(item.get("source_id") or ""),
        )
    )
    platform_counts = Counter(item["platform"] for item in queue_items)
    return {
        "generated_at": report.get("generated_at", ""),
        "description": "Deterministic work queue for non-live-capturable sources that need authorized seeds, exports, or approved API access.",
        "inputs": report.get("inputs", {}),
        "summary": {
            "queue_count": len(queue_items),
            "platform_counts": dict(sorted(platform_counts.items())),
            "priority_order": [
                platform
                for platform, _rank in sorted(PLATFORM_PRIORITY.items(), key=lambda row: row[1])
                if platform_counts.get(platform, 0)
            ],
        },
        "items": queue_items,
    }


def seed_template_for_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "target_path": item.get("preferred_seed_path", ""),
        "source_id": item.get("source_id", ""),
        "agency_id": item.get("agency_id", ""),
        "agency_name": item.get("agency_name", ""),
        "platform": item.get("platform", ""),
        "source_url": item.get("url", ""),
        "account": item.get("account", ""),
        "authorization_note": "Replace this template with operator-authorized export data before placing it under manual_archive_seeds/.",
        "posts": [
            {
                "post_id": "stable-platform-id-or-operator-id",
                "url": "https://example.govt.nz/or/platform/post",
                "created_at": "2026-07-01T00:00:00Z",
                "text": "Archived public or operator-authorized content.",
                "media": [
                    {
                        "url": "https://example.govt.nz/media.jpg",
                        "media_type": "image",
                        "alt_text": "Optional description",
                    }
                ],
            }
        ],
    }


def build_next_batch_templates(report: dict[str, Any], *, limit: int = 25) -> dict[str, Any]:
    work_queue = build_work_queue(report)
    items = work_queue.get("items", [])[:limit]
    return {
        "generated_at": report.get("generated_at", ""),
        "description": "Source-specific starter templates for the next deterministic manual seed batch. These are not seed files and do not mark sources as seed_present.",
        "summary": {
            "template_count": len(items),
            "limit": limit,
            "platform_counts": dict(sorted(Counter(item.get("platform", "") for item in items).items())),
        },
        "templates": [seed_template_for_item(item) for item in items],
    }


def write_drop_targets(path: Path, templates: dict[str, Any]) -> None:
    lines = [
        "# Manual Seed Drop Targets",
        "",
        "Use these paths to place operator-authorized seed JSON files for the next deterministic batch.",
        "The templates below are derived from `conductor/manual_seed_next_batch_templates.json` and do not create live seed files by themselves.",
        "",
        f"Generated: {templates.get('generated_at', '')}",
        "",
        "## Summary",
        "",
    ]
    summary = templates.get("summary", {})
    lines.append(f"- `template_count`: {summary.get('template_count', 0)}")
    lines.append(f"- `limit`: {summary.get('limit', 0)}")
    lines.append("")
    lines.append("| Platform | Source | Seed path |")
    lines.append("| --- | --- | --- |")
    for item in templates.get("templates", []):
        lines.append(
            "| "
            f"`{item.get('platform', '')}` | "
            f"`{item.get('source_id', '')}` | "
            f"`{item.get('target_path', '')}` |"
        )
    lines.extend(
        [
            "",
            "## Shape",
            "",
            "```json",
            json.dumps((templates.get("templates") or [{}])[0], indent=2, sort_keys=True),
            "```",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_json(args.manifest)
    policy = load_json(args.policy)
    platform_policy = policy.get("platforms", {})
    requested = [platform.strip() for platform in args.platforms.split(",") if platform.strip()]
    items = []
    for source in manifest.get("sources", []):
        platform = str(source.get("platform") or "")
        if platform not in requested:
            continue
        if platform not in platform_policy:
            continue
        items.append(onboarding_item(source, platform_policy[platform], args.manual_seed_root))
    status_counts = Counter(item["onboarding_status"] for item in items)
    platform_counts = Counter(item["platform"] for item in items)
    status_by_platform: dict[str, dict[str, int]] = {}
    for item in items:
        platform = item["platform"]
        statuses = status_by_platform.setdefault(platform, {})
        statuses[item["onboarding_status"]] = statuses.get(item["onboarding_status"], 0) + 1
    remaining_groups = {
        platform: counts.get("needs_authorized_seed_or_api", 0)
        for platform, counts in status_by_platform.items()
        if counts.get("needs_authorized_seed_or_api", 0) > 0
    }
    return {
        "generated_at": now_iso(),
        "description": "Explicit onboarding queue for Meta, LinkedIn, and X sources requiring authorized seeds, owner exports, approved APIs, or lawful public archive inputs.",
        "inputs": {
            "manifest": str(args.manifest),
            "policy": str(args.policy),
            "manual_seed_root": str(args.manual_seed_root),
            "platforms": requested,
        },
        "summary": {
            "selected_sources": len(items),
            "platform_counts": dict(sorted(platform_counts.items())),
            "status_counts": dict(sorted(status_counts.items())),
            "status_by_platform": {platform: dict(sorted(counts.items())) for platform, counts in sorted(status_by_platform.items())},
            "remaining_groups": dict(sorted(remaining_groups.items())),
            "remaining_group_count": len(remaining_groups),
            "remaining_source_count": sum(remaining_groups.values()),
        },
        "platform_policies": {platform: platform_policy[platform] for platform in requested if platform in platform_policy},
        "items": sorted(items, key=lambda item: (item["platform"], item["agency_id"], item["source_id"])),
    }


def write_summary(path: Path, report: dict[str, Any]) -> None:
    summary = report.get("summary", {})
    work_queue = build_work_queue(report)
    next_items = work_queue.get("items", [])[:25]
    lines = [
        "# Manual/API Source Onboarding",
        "",
        f"Generated: {report.get('generated_at', '')}",
        "",
        "## Summary",
        "",
        f"- `selected_sources`: {summary.get('selected_sources', 0)}",
        f"- `remaining_group_count`: {summary.get('remaining_group_count', 0)}",
        f"- `remaining_source_count`: {summary.get('remaining_source_count', 0)}",
        "",
        "## Remaining groups",
        "",
    ]
    remaining_groups = summary.get("remaining_groups", {})
    if remaining_groups:
        for platform, count in remaining_groups.items():
            lines.append(f"- `{platform}`: {count}")
    else:
        lines.append("- None")
    lines.extend(
        [
            "",
            "## Platform status",
            "",
        ]
    )
    for platform, counts in summary.get("status_by_platform", {}).items():
        lines.append(f"- `{platform}`: {counts}")
    lines.extend(
        [
            "",
            "## Next deterministic batch",
            "",
        ]
    )
    if next_items:
        lines.append("| Platform | Source | Agency | Preferred seed path |")
        lines.append("| --- | --- | --- | --- |")
        for item in next_items:
            lines.append(
                "| "
                f"`{item.get('platform', '')}` | "
                f"`{item.get('source_id', '')}` | "
                f"{item.get('agency_name') or item.get('agency_id') or ''} | "
                f"`{item.get('preferred_seed_path', '')}` |"
            )
    else:
        lines.append("- None")
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- This queue is for Facebook, Instagram, Threads, LinkedIn, X, and newsletters.",
            "- `seed_present` sources are ready for archival processing.",
            "- `needs_authorized_seed_or_api` sources remain in the manual/API remainder set.",
            "- `conductor/manual_seed_work_queue.json` lists the remaining sources in deterministic execution order with preferred seed paths.",
            "- `conductor/manual_seed_next_batch_templates.json` contains source-specific starter JSON for the next deterministic batch without creating live seed files.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build explicit manual/API onboarding queue for non-live-capturable platforms.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--next-batch-templates", type=Path, default=DEFAULT_NEXT_BATCH_TEMPLATES)
    parser.add_argument("--drop-targets", type=Path, default=DEFAULT_DROP_TARGETS)
    parser.add_argument("--manual-seed-root", type=Path, default=DEFAULT_MANUAL_SEED_ROOT)
    parser.add_argument("--platforms", default=",".join(DEFAULT_PLATFORMS))
    args = parser.parse_args()
    report = build_report(args)
    write_json(args.report, report)
    write_summary(args.summary, report)
    queue = build_work_queue(report)
    templates = build_next_batch_templates(report)
    write_json(args.queue, queue)
    write_json(args.next_batch_templates, templates)
    write_drop_targets(args.drop_targets, templates)
    print(
        "Manual/API onboarding report wrote "
        f"{report['summary']['selected_sources']} selected sources."
    )


if __name__ == "__main__":
    main()
