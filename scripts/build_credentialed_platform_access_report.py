import argparse
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_MANIFEST = Path("conductor/govt_archive_source_manifest.json")
DEFAULT_POLICY = Path("config/credentialed_platform_access.json")
DEFAULT_REPORT = Path("conductor/credentialed_platform_access_report.json")
DEFAULT_SUMMARY = Path("conductor/credentialed_platform_access_summary.md")
DEFAULT_MANUAL_SEED_ROOT = Path("manual_archive_seeds")
DEFAULT_PLATFORMS = ["threads", "x", "linkedin", "facebook", "instagram"]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def env_enabled(name: str, enabled_value: str) -> bool:
    return os.getenv(name, "").strip().lower() == enabled_value.strip().lower()


def secret_set_present(secret_set: list[str]) -> bool:
    return all(os.getenv(secret, "").strip() for secret in secret_set)


def matching_secret_sets(required_secret_sets: list[list[str]]) -> list[list[str]]:
    return [secret_set for secret_set in required_secret_sets if secret_set_present(secret_set)]


def seed_candidates(source: dict[str, Any], seed_directory: str) -> list[str]:
    source_id = str(source.get("source_id") or "")
    agency_id = str(source.get("agency_id") or "")
    directory = seed_directory.replace("\\", "/")
    return [
        f"{directory}/{source_id}.json" if source_id else "",
        f"{directory}/{agency_id}.json" if agency_id else "",
    ]


def seed_present(candidates: list[str]) -> bool:
    return any(candidate and Path(candidate).is_file() for candidate in candidates)


def readiness_status(policy: dict[str, Any], enabled: bool, present_sets: list[list[str]]) -> str:
    if not enabled:
        return str(policy.get("disabled_status") or "api_disabled_manual_seed_path")
    if not present_sets:
        return str(policy.get("enabled_missing_secret_status") or "api_enabled_missing_secret")
    return str(policy.get("enabled_ready_status") or "api_enabled_ready")


def source_item(source: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    gate_variable = str(policy.get("gate_variable") or "")
    enabled_value = str(policy.get("enabled_value") or "true")
    required_secret_sets = policy.get("required_secret_sets") or []
    normalized_secret_sets = [[str(secret) for secret in secret_set] for secret_set in required_secret_sets]
    present_sets = matching_secret_sets(normalized_secret_sets)
    enabled = env_enabled(gate_variable, enabled_value) if gate_variable else False
    candidates = [candidate for candidate in seed_candidates(source, str(policy.get("seed_directory") or "")) if candidate]
    return {
        "source_id": source.get("source_id", ""),
        "agency_id": source.get("agency_id", ""),
        "agency_name": source.get("agency_name", ""),
        "platform": source.get("platform", ""),
        "source_type": source.get("source_type", ""),
        "url": source.get("url", ""),
        "account": source.get("account", ""),
        "archive_status": source.get("archive_status", ""),
        "feasibility": source.get("feasibility", ""),
        "live_capture_enabled": enabled,
        "gate_variable": gate_variable,
        "gate_enabled_value": enabled_value,
        "readiness_status": readiness_status(policy, enabled, present_sets),
        "default_capture_path": policy.get("default_capture_path", ""),
        "required_secret_sets": normalized_secret_sets,
        "present_secret_set_count": len(present_sets),
        "required_secrets_present": bool(present_sets),
        "optional_variables": policy.get("optional_variables", []),
        "seed_candidates": candidates,
        "seed_present": seed_present(candidates),
        "permission_error_statuses": policy.get("permission_error_statuses", []),
        "issue_policy": policy.get("issue_policy", ""),
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_json(args.manifest)
    policy = load_json(args.policy)
    platform_policy = policy.get("platforms", {})
    requested = [platform.strip() for platform in args.platforms.split(",") if platform.strip()]
    items = []
    for source in manifest.get("sources", []):
        platform = str(source.get("platform") or "")
        if platform not in requested or platform not in platform_policy:
            continue
        items.append(source_item(source, platform_policy[platform]))

    status_counts = Counter(item["readiness_status"] for item in items)
    platform_counts = Counter(item["platform"] for item in items)
    status_by_platform: dict[str, dict[str, int]] = {}
    enabled_by_platform: dict[str, int] = {}
    seed_present_by_platform: dict[str, int] = {}
    for item in items:
        platform = item["platform"]
        statuses = status_by_platform.setdefault(platform, {})
        statuses[item["readiness_status"]] = statuses.get(item["readiness_status"], 0) + 1
        if item["live_capture_enabled"]:
            enabled_by_platform[platform] = enabled_by_platform.get(platform, 0) + 1
        if item["seed_present"]:
            seed_present_by_platform[platform] = seed_present_by_platform.get(platform, 0) + 1

    actionable_statuses = {"api_enabled_missing_secret"}
    actionable_items = [item for item in items if item["readiness_status"] in actionable_statuses]
    return {
        "generated_at": now_iso(),
        "description": "Credentialed platform live-capture readiness. Disabled gates are report-only states; enabled gates with missing credentials are actionable configuration faults.",
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
            "live_capture_enabled_by_platform": dict(sorted(enabled_by_platform.items())),
            "seed_present_by_platform": dict(sorted(seed_present_by_platform.items())),
            "actionable_configuration_fault_count": len(actionable_items),
        },
        "platform_policies": {platform: platform_policy[platform] for platform in requested if platform in platform_policy},
        "actionable_configuration_faults": sorted(actionable_items, key=lambda item: (item["platform"], item["agency_id"], item["source_id"])),
        "items": sorted(items, key=lambda item: (item["platform"], item["agency_id"], item["source_id"])),
    }


def write_summary(path: Path, report: dict[str, Any]) -> None:
    summary = report.get("summary", {})
    lines = [
        "# Credentialed Platform Access Readiness",
        "",
        f"Generated: {report.get('generated_at', '')}",
        "",
        "## Summary",
        "",
        f"- `selected_sources`: {summary.get('selected_sources', 0)}",
        f"- `actionable_configuration_fault_count`: {summary.get('actionable_configuration_fault_count', 0)}",
        "",
        "## Platform status",
        "",
    ]
    for platform, counts in summary.get("status_by_platform", {}).items():
        lines.append(f"- `{platform}`: {counts}")
    lines.extend([
        "",
        "## Policy",
        "",
        "- Disabled live API gates are report-only states and must not open blocker issues.",
        "- Enabled live API gates with missing required secrets are actionable configuration faults.",
        "- Registered-but-unseeded credentialed accounts are not described as archived until records exist.",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build credentialed platform live-capture readiness report.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--manual-seed-root", type=Path, default=DEFAULT_MANUAL_SEED_ROOT)
    parser.add_argument("--platforms", default=",".join(DEFAULT_PLATFORMS))
    args = parser.parse_args()
    report = build_report(args)
    write_json(args.report, report)
    write_summary(args.summary, report)
    print(
        "Credentialed platform access report wrote "
        f"{report['summary']['selected_sources']} selected sources."
    )


if __name__ == "__main__":
    main()
