import argparse
import json
from pathlib import Path
from typing import Any, TypedDict

OPEN_PLATFORMS = {"bluesky", "mastodon", "rss"}
PROPRIETARY_PLATFORMS = {
    "x",
    "threads",
    "facebook",
    "instagram",
    "youtube",
    "tiktok",
    "linkedin",
}
ALL_PLATFORMS = sorted(OPEN_PLATFORMS | PROPRIETARY_PLATFORMS)
ACTIVE_STATUS = "active"


class GapReport(TypedDict):
    agency_count: int
    platform_coverage: dict[str, int]
    open_network_coverage: int
    proprietary_network_coverage: int
    proprietary_without_open: list[dict[str, Any]]
    open_missing: list[dict[str, Any]]
    deactivated_profiles: list[dict[str, str]]


def load_registry(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list):
        raise ValueError("Registry must be a list of agency records.")
    return data


def analyze_registry(agencies: list[dict[str, Any]]) -> GapReport:
    platform_coverage = {platform: 0 for platform in ALL_PLATFORMS}
    proprietary_without_open: list[dict[str, Any]] = []
    open_missing: list[dict[str, Any]] = []
    deactivated_profiles: list[dict[str, str]] = []
    open_count = 0
    proprietary_count = 0

    for agency in agencies:
        profiles = agency.get("social_profiles", {})
        active_platforms = {
            platform
            for platform, profile in profiles.items()
            if isinstance(profile, dict) and profile.get("status") == ACTIVE_STATUS
        }
        for platform in active_platforms:
            if platform in platform_coverage:
                platform_coverage[platform] += 1

        open_active = sorted(active_platforms & OPEN_PLATFORMS)
        proprietary_active = sorted(active_platforms & PROPRIETARY_PLATFORMS)
        if open_active:
            open_count += 1
        if proprietary_active:
            proprietary_count += 1
        if proprietary_active and not open_active:
            proprietary_without_open.append(_agency_gap(agency, proprietary_active, []))
        if not open_active:
            open_missing.append(_agency_gap(agency, proprietary_active, sorted(OPEN_PLATFORMS)))

        for platform, profile in profiles.items():
            if isinstance(profile, dict) and profile.get("status") in {"inactive", "deactivated"}:
                deactivated_profiles.append(
                    {
                        "agency_id": str(agency.get("agency_id", "")),
                        "name": str(agency.get("name", "")),
                        "platform": str(platform),
                        "status": str(profile.get("status", "")),
                        "deactivated_at": str(profile.get("deactivated_at", "")),
                    }
                )

    return {
        "agency_count": len(agencies),
        "platform_coverage": platform_coverage,
        "open_network_coverage": open_count,
        "proprietary_network_coverage": proprietary_count,
        "proprietary_without_open": proprietary_without_open,
        "open_missing": open_missing,
        "deactivated_profiles": deactivated_profiles,
    }


def write_report(report: GapReport, path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2, ensure_ascii=False, sort_keys=True)
        file.write("\n")


def _agency_gap(
    agency: dict[str, Any],
    active_proprietary: list[str],
    missing_open: list[str],
) -> dict[str, Any]:
    return {
        "agency_id": agency.get("agency_id", ""),
        "name": agency.get("name", ""),
        "type": agency.get("type", ""),
        "portfolio": agency.get("portfolio", ""),
        "active_proprietary": active_proprietary,
        "missing_open": missing_open,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate registry social gap analysis.")
    parser.add_argument("--registry", default="registry/agencies.json")
    parser.add_argument("--output", default="registry/gap_analysis.json")
    args = parser.parse_args()

    report = analyze_registry(load_registry(args.registry))
    write_report(report, args.output)


if __name__ == "__main__":
    main()