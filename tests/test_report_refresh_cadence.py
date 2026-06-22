from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

from scripts.report_refresh_cadence import build_refresh_report


SCRIPT = Path("scripts/report_refresh_cadence.py")


def _write_json(path: Path, payload: list[dict]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_registry(
    registry_dir: Path,
    *,
    agencies: list[dict] | None = None,
    parties: list[dict] | None = None,
    persons: list[dict] | None = None,
) -> None:
    registry_dir.mkdir(exist_ok=True)
    _write_json(registry_dir / "government_directory.json", agencies or [])
    _write_json(registry_dir / "parties.json", parties or [])
    _write_json(registry_dir / "persons.json", persons or [])


def test_report_groups_monthly_and_event_triggered_records(tmp_path: Path) -> None:
    agencies = [
        {
            "agency_id": "ministry-example",
            "name": "Ministry Example",
            "type": "Department",
            "official_website": "https://example.govt.nz",
            "status": "active",
            "social_profiles": {
                "x": {
                    "handle": "MinExample",
                    "url": "https://x.com/MinExample",
                    "status": "active",
                    "last_checked_at": "2026-05-21",
                    "last_seen_at": "2026-06-01",
                    "verification_status": "current",
                },
                "facebook": {
                    "handle": "MinExample",
                    "url": "https://www.facebook.com/MinExample",
                    "status": "active",
                    "last_checked_at": "2026-06-10",
                    "verification_status": "current",
                },
                "bluesky": {
                    "handle": "min.example.govt.nz",
                    "url": "https://bsky.app/profile/min.example.govt.nz",
                    "status": "active",
                    "last_checked_at": "2026-06-16",
                    "verification_status": "current",
                },
            },
        }
    ]
    _write_registry(tmp_path, agencies=agencies)

    report = build_refresh_report(
        registry_dir=tmp_path,
        as_of=date(2026, 6, 22),
    )

    agency_records = report["groups"]["agencies"]
    assert [record["id"] for record in agency_records] == ["ministry-example"]
    agency_by_platform = {
        item["platform"]: item for item in agency_records[0]["due_profiles"]
    }
    assert set(agency_by_platform) == {"x"}
    assert agency_by_platform["x"]["cadence_days"] == 30
    assert agency_by_platform["x"]["reason"] == "monthly-stale"
    assert agency_by_platform["x"]["days_since_checked"] == 32
    assert report["summary"]["agencies"]["profiles_due"] == 1


def test_event_triggered_records_are_due_before_event_date(tmp_path: Path) -> None:
    parties = [
        {
            "party_id": "example-party",
            "name": "Example Party",
            "status": "active",
            "social_profiles": {
                "instagram": {
                    "handle": "exampleparty",
                    "url": "https://www.instagram.com/exampleparty",
                    "status": "active",
                    "last_checked_at": "2026-06-12",
                    "verification_status": "current",
                },
                "youtube": {
                    "handle": "@ExampleParty",
                    "url": "https://www.youtube.com/@ExampleParty",
                    "status": "active",
                    "last_checked_at": "2026-06-16",
                    "verification_status": "current",
                },
            },
        }
    ]
    _write_registry(tmp_path, parties=parties)

    report = build_refresh_report(
        registry_dir=tmp_path,
        as_of=date(2026, 6, 22),
        event_date=date(2026, 6, 15),
        event_name="Cabinet reshuffle",
    )

    party_records = report["groups"]["parties"]
    assert [record["id"] for record in party_records] == ["example-party"]
    due_by_platform = {item["platform"]: item for item in party_records[0]["due_profiles"]}
    assert set(due_by_platform) == {"instagram"}
    assert due_by_platform["instagram"]["reason"] == "event-triggered"
    assert due_by_platform["instagram"]["event_date"] == "2026-06-15"
    assert due_by_platform["instagram"]["event_name"] == "Cabinet reshuffle"


def test_report_separates_mps_public_leaders_and_historical_figures(
    tmp_path: Path,
) -> None:
    persons = [
        {
            "person_id": "current-mp",
            "full_name": "Current MP",
            "social_profiles": {
                "x": {
                    "handle": "CurrentMP",
                    "url": "https://x.com/CurrentMP",
                    "status": "active",
                    "last_checked_at": "2026-05-22",
                    "verification_status": "current",
                }
            },
            "roles": [
                {
                    "role_id": "mp-role",
                    "title": "Member of Parliament",
                    "organization": "nz-parliament",
                    "category": "mp",
                    "is_current": True,
                }
            ],
        },
        {
            "person_id": "current-leader",
            "full_name": "Current Leader",
            "social_profiles": {
                "linkedin": {
                    "handle": "current-leader",
                    "url": "https://www.linkedin.com/in/current-leader",
                    "status": "active",
                    "verification_status": "current",
                }
            },
            "roles": [
                {
                    "role_id": "ce-role",
                    "title": "Chief Executive",
                    "organization": "example-agency",
                    "category": "chief-executive",
                    "is_current": True,
                }
            ],
        },
        {
            "person_id": "former-member",
            "full_name": "Former Member",
            "social_profiles": {
                "facebook": {
                    "handle": "FormerMember",
                    "url": "https://www.facebook.com/FormerMember",
                    "status": "inactive",
                    "last_checked_at": "2025-06-21",
                    "verification_status": "historical",
                }
            },
            "roles": [
                {
                    "role_id": "former-mp-role",
                    "title": "Former Member of Parliament",
                    "organization": "nz-parliament",
                    "category": "mp",
                    "is_current": False,
                }
            ],
        },
    ]
    _write_registry(tmp_path, persons=persons)

    report = build_refresh_report(
        registry_dir=tmp_path,
        as_of=date(2026, 6, 22),
    )

    assert [item["id"] for item in report["groups"]["mps"]] == ["current-mp"]
    mp_profile = report["groups"]["mps"][0]["due_profiles"][0]
    assert mp_profile["cadence_days"] == 30
    assert mp_profile["reason"] == "monthly-stale"

    assert [item["id"] for item in report["groups"]["public_sector_leaders"]] == [
        "current-leader"
    ]
    leader_profile = report["groups"]["public_sector_leaders"][0]["due_profiles"][0]
    assert leader_profile["reason"] == "missing-last-checked-at"

    assert [item["id"] for item in report["groups"]["historical_figures"]] == [
        "former-member"
    ]
    historical_profile = report["groups"]["historical_figures"][0]["due_profiles"][0]
    assert historical_profile["cadence_days"] == 365
    assert historical_profile["reason"] == "annual-stale"


def test_unknown_verification_status_is_manual_review_due(tmp_path: Path) -> None:
    parties = [
        {
            "party_id": "unknown-party",
            "name": "Unknown Party",
            "status": "active",
            "social_profiles": {
                "x": {
                    "handle": "UnknownParty",
                    "url": "https://x.com/UnknownParty",
                    "status": "active",
                    "last_checked_at": "2026-06-20",
                    "verification_status": "unknown",
                }
            },
        }
    ]
    _write_registry(tmp_path, parties=parties)

    report = build_refresh_report(
        registry_dir=tmp_path,
        as_of=date(2026, 6, 22),
    )

    assert len(report["groups"]["parties"]) == 1
    manual_profile = report["groups"]["parties"][0]["manual_review_profiles"][0]
    assert manual_profile["reason"] == "unknown-verification-status"


def test_cli_writes_json_report_without_mutating_inputs(tmp_path: Path) -> None:
    registry_dir = tmp_path / "registry"
    output_path = tmp_path / "refresh_report.json"
    agencies = [
        {
            "agency_id": "example-agency",
            "name": "Example \u0100gency",
            "type": "Department",
            "official_website": "https://example.govt.nz",
            "status": "active",
            "social_profiles": {
                "x": {
                    "handle": "ExampleAgency",
                    "url": "https://x.com/ExampleAgency",
                    "status": "active",
                    "last_checked_at": "2026-05-01",
                    "verification_status": "current",
                }
            },
        }
    ]
    _write_registry(registry_dir, agencies=agencies)
    agencies_path = registry_dir / "government_directory.json"
    original_agencies = agencies_path.read_text(encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--registry-dir",
            str(registry_dir),
            "--as-of",
            "2026-06-22",
            "--output",
            str(output_path),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert agencies_path.read_text(encoding="utf-8") == original_agencies
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["summary"]["agencies"]["profiles_due"] == 1
    assert payload["summary"]["total"]["profiles_due"] == 1
    assert json.loads(result.stdout) == payload
