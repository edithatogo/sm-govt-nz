"""Report registry social profiles that are stale or due for manual review."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_REGISTRY_DIR = Path("registry")
DEFAULT_OUTPUT_PATH = Path("conductor/registry_refresh_report.json")

CURRENT_CADENCE_DAYS = 30
HISTORICAL_CADENCE_DAYS = 365
CURRENT_GROUPS = ("agencies", "parties", "mps", "public_sector_leaders")
ALL_GROUPS = (*CURRENT_GROUPS, "historical_figures")
VERIFICATION_STATUSES = {
    "current",
    "inactive",
    "deactivated",
    "historical",
    "unknown",
}
HISTORICAL_PROFILE_STATUSES = {"inactive", "deactivated", "historical"}
PUBLIC_SECTOR_ROLE_CATEGORIES = {
    "auditor-general",
    "chief-executive",
    "commissioner",
    "defence-chief",
    "governor-general",
    "judge",
    "local-government-ceo",
    "ombudsman",
    "police-commissioner",
    "reserve-bank-governor",
    "statutory-officer",
}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def parse_date(value: Any) -> date | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def parse_report_date(value: str | None, *, default: date | None = None) -> date:
    if value is None:
        if default is None:
            return date.today()
        return default
    parsed = parse_date(value)
    if parsed is None:
        raise ValueError(f"invalid date: {value}")
    return parsed


def profile_verification_status(profile: dict[str, Any], record_status: str) -> str:
    explicit = profile.get("verification_status")
    if explicit in VERIFICATION_STATUSES:
        return explicit

    profile_status = profile.get("status")
    if profile_status == "active":
        return "current"
    if profile_status in {"inactive", "deactivated"}:
        return profile_status
    if profile_status == "archived":
        return "historical"

    if record_status in {"active", "current"}:
        return "current"
    if record_status in {"inactive", "deactivated", "deregistered", "historical"}:
        return "historical"
    return "unknown"


def cadence_days_for(status: str, record_group: str) -> int:
    if status in HISTORICAL_PROFILE_STATUSES or record_group == "historical_figures":
        return HISTORICAL_CADENCE_DAYS
    return CURRENT_CADENCE_DAYS


def evaluate_profile(
    *,
    platform: str,
    profile: dict[str, Any],
    record_status: str,
    record_group: str,
    as_of: date,
    event_date: date | None,
    event_name: str | None,
) -> dict[str, Any]:
    verification_status = profile_verification_status(profile, record_status)
    checked_at = parse_date(profile.get("last_checked_at"))
    seen_at = parse_date(profile.get("last_seen_at"))
    cadence_days = cadence_days_for(verification_status, record_group)

    result: dict[str, Any] = {
        "platform": platform,
        "handle": profile.get("handle", ""),
        "url": profile.get("url", ""),
        "status": profile.get("status", record_status),
        "verification_status": verification_status,
        "last_checked_at": profile.get("last_checked_at"),
        "last_seen_at": profile.get("last_seen_at"),
        "cadence_days": cadence_days,
        "due": False,
        "manual_review": False,
        "reason": None,
    }

    if isinstance(profile.get("last_checked_at"), str) and checked_at is None:
        result.update({"manual_review": True, "reason": "invalid-last-checked-at"})
        return result
    if isinstance(profile.get("last_seen_at"), str) and seen_at is None:
        result.update({"manual_review": True, "reason": "invalid-last-seen-at"})
        return result
    if verification_status == "unknown":
        result.update({"manual_review": True, "reason": "unknown-verification-status"})
        return result
    if checked_at is None:
        result.update({"due": True, "reason": "missing-last-checked-at"})
        return result
    if (
        event_date
        and checked_at < event_date
        and record_group in CURRENT_GROUPS
        and cadence_days == CURRENT_CADENCE_DAYS
    ):
        result.update(
            {
                "due": True,
                "reason": "event-triggered",
                "event_date": event_date.isoformat(),
                "event_name": event_name,
            }
        )
        return result

    days_since_checked = (as_of - checked_at).days
    result["days_since_checked"] = days_since_checked
    if days_since_checked > cadence_days:
        reason = "annual-stale" if cadence_days == HISTORICAL_CADENCE_DAYS else "monthly-stale"
        result.update({"due": True, "reason": reason})

    return result


def current_role_categories(person: dict[str, Any]) -> set[str]:
    return {
        role.get("category", "")
        for role in person.get("roles", [])
        if isinstance(role, dict) and role.get("is_current") is True
    }


def person_group(person: dict[str, Any]) -> str:
    categories = current_role_categories(person)
    if "mp" in categories or (
        person.get("member_type") in {"electorate", "list"} and categories
    ):
        return "mps"
    if categories & PUBLIC_SECTOR_ROLE_CATEGORIES:
        return "public_sector_leaders"
    return "historical_figures"


def assess_record(
    *,
    record_id: str,
    name: str,
    record_status: str,
    record_group: str,
    profiles: dict[str, Any],
    as_of: date,
    event_date: date | None,
    event_name: str | None,
) -> dict[str, Any] | None:
    due_profiles: list[dict[str, Any]] = []
    manual_review_profiles: list[dict[str, Any]] = []

    for platform, profile in sorted(profiles.items()):
        if not isinstance(profile, dict):
            manual_review_profiles.append(
                {
                    "platform": platform,
                    "manual_review": True,
                    "reason": "malformed-profile-record",
                }
            )
            continue

        result = evaluate_profile(
            platform=platform,
            profile=profile,
            record_status=record_status,
            record_group=record_group,
            as_of=as_of,
            event_date=event_date,
            event_name=event_name,
        )
        if result["manual_review"]:
            manual_review_profiles.append(result)
        elif result["due"]:
            due_profiles.append(result)

    if not due_profiles and not manual_review_profiles:
        return None

    return {
        "id": record_id,
        "name": name,
        "status": record_status,
        "profile_count": len(profiles),
        "due_profiles": due_profiles,
        "manual_review_profiles": manual_review_profiles,
    }


def empty_summary() -> dict[str, int]:
    return {
        "total_records": 0,
        "total_profiles": 0,
        "records_due": 0,
        "profiles_due": 0,
        "records_manual_review": 0,
        "profiles_manual_review": 0,
    }


def add_summary(summary: dict[str, int], profiles: dict[str, Any], record: dict[str, Any] | None) -> None:
    summary["total_records"] += 1
    summary["total_profiles"] += len(profiles)
    if record is None:
        return
    due_count = len(record["due_profiles"])
    manual_count = len(record["manual_review_profiles"])
    if due_count:
        summary["records_due"] += 1
        summary["profiles_due"] += due_count
    if manual_count:
        summary["records_manual_review"] += 1
        summary["profiles_manual_review"] += manual_count


def build_refresh_report(
    *,
    registry_dir: Path = DEFAULT_REGISTRY_DIR,
    as_of: date | None = None,
    event_date: date | None = None,
    event_name: str | None = None,
) -> dict[str, Any]:
    as_of = as_of or date.today()
    agencies = load_json(registry_dir / "government_directory.json")
    parties = load_json(registry_dir / "parties.json")
    persons = load_json(registry_dir / "persons.json")

    groups: dict[str, list[dict[str, Any]]] = {group: [] for group in ALL_GROUPS}
    summary: dict[str, dict[str, int]] = {group: empty_summary() for group in ALL_GROUPS}

    for agency in agencies:
        profiles = agency.get("social_profiles", {})
        record = assess_record(
            record_id=agency["agency_id"],
            name=agency["name"],
            record_status=agency.get("status", "unknown"),
            record_group="agencies",
            profiles=profiles,
            as_of=as_of,
            event_date=event_date,
            event_name=event_name,
        )
        add_summary(summary["agencies"], profiles, record)
        if record:
            groups["agencies"].append(record)

    for party in parties:
        profiles = party.get("social_profiles", {})
        record = assess_record(
            record_id=party["party_id"],
            name=party["name"],
            record_status=party.get("status", "unknown"),
            record_group="parties",
            profiles=profiles,
            as_of=as_of,
            event_date=event_date,
            event_name=event_name,
        )
        add_summary(summary["parties"], profiles, record)
        if record:
            groups["parties"].append(record)

    for person in persons:
        group = person_group(person)
        profiles = person.get("social_profiles", {})
        status = "current" if group != "historical_figures" else "historical"
        record = assess_record(
            record_id=person["person_id"],
            name=person["full_name"],
            record_status=status,
            record_group=group,
            profiles=profiles,
            as_of=as_of,
            event_date=event_date,
            event_name=event_name,
        )
        add_summary(summary[group], profiles, record)
        if record:
            groups[group].append(record)

    total = empty_summary()
    for group_summary in summary.values():
        for key, value in group_summary.items():
            total[key] += value

    return {
        "tool": "report_refresh_cadence",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "as_of_date": as_of.isoformat(),
        "registry_dir": str(registry_dir),
        "cadence_days": {
            "current_operational": CURRENT_CADENCE_DAYS,
            "historical_or_inactive": HISTORICAL_CADENCE_DAYS,
        },
        "event": {
            "date": event_date.isoformat() if event_date else None,
            "name": event_name,
        },
        "summary": {"total": total, **summary},
        "groups": groups,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--registry-dir",
        type=Path,
        default=DEFAULT_REGISTRY_DIR,
        help="Directory containing government_directory.json, parties.json, and persons.json.",
    )
    parser.add_argument(
        "--as-of",
        help="Date to evaluate cadence against, in YYYY-MM-DD format. Defaults to today.",
    )
    parser.add_argument(
        "--event-date",
        help="Optional event date requiring current records to be rechecked afterward.",
    )
    parser.add_argument(
        "--event-name",
        help="Label for the event-triggered refresh cohort.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help=f"Optional path to write report JSON, e.g. {DEFAULT_OUTPUT_PATH}.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        report = build_refresh_report(
            registry_dir=args.registry_dir,
            as_of=parse_report_date(args.as_of),
            event_date=parse_report_date(args.event_date, default=None) if args.event_date else None,
            event_name=args.event_name,
        )
    except (OSError, ValueError, json.JSONDecodeError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    report_json = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report_json + "\n", encoding="utf-8")
    print(report_json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
