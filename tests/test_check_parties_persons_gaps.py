"""Tests for scripts/check_parties_persons_gaps.py."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path("scripts/check_parties_persons_gaps.py")


def _run(args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
    )


def _write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _registry(tmp_path: Path, *, persons=None, parties=None, agencies=None) -> Path:
    registry_dir = tmp_path / "registry"
    registry_dir.mkdir()
    _write_json(
        registry_dir / "parties.json",
        parties
        if parties is not None
        else [
            {
                "party_id": "example-party",
                "name": "Example Party",
                "status": "active",
                "leader_person_id": "example-person",
            }
        ],
    )
    _write_json(
        registry_dir / "government_directory.json",
        agencies
        if agencies is not None
        else [
            {
                "agency_id": "nz-parliament",
                "name": "New Zealand Parliament",
                "type": "Parliament",
                "official_website": "https://www.parliament.nz",
                "status": "active",
                "social_profiles": {},
            }
        ],
    )
    _write_json(
        registry_dir / "persons.json",
        persons
        if persons is not None
        else [
            {
                "person_id": "example-person",
                "full_name": "Example Person",
                "party_id": "example-party",
                "roles": [
                    {
                        "role_id": "example-role",
                        "title": "Member",
                        "organization": "nz-parliament",
                        "category": "mp",
                        "is_current": True,
                    }
                ],
            }
        ],
    )
    return registry_dir


def test_help_exits_zero():
    result = _run(["--help"])
    assert result.returncode == 0
    assert "--report" in result.stdout
    assert "--registry-dir" in result.stdout


def test_missing_report_passes_when_not_strict_and_using_report():
    missing = Path("conductor/_missing_for_test.json")
    if missing.exists():
        missing.unlink()
    result = _run(["--report", str(missing), "--use-report"])
    assert result.returncode == 0


def test_missing_report_fails_when_strict_and_using_report():
    missing = Path("conductor/_missing_for_test.json")
    if missing.exists():
        missing.unlink()
    result = _run(["--report", str(missing), "--strict", "--use-report"])
    assert result.returncode == 1


def test_zero_gaps_passes_strict_from_recomputed_registry(tmp_path):
    registry_dir = _registry(tmp_path)

    result = _run(["--registry-dir", str(registry_dir), "--strict"])

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["report_source"] == "recomputed"
    assert payload["complete"] is True


def test_default_recomputes_and_stale_clean_report_cannot_hide_drift(tmp_path):
    registry_dir = _registry(
        tmp_path,
        persons=[
            {
                "person_id": "orphan-person",
                "full_name": "Orphan Person",
                "party_id": "example-party",
                "roles": [
                    {
                        "role_id": "bad-role",
                        "title": "Bad Role",
                        "organization": "missing-agency",
                        "category": "mp",
                        "is_current": True,
                    }
                ],
            }
        ],
    )
    stale = tmp_path / "stale-clean-report.json"
    _write_json(
        stale,
        {
            "missing_party_leaders": [],
            "missing_party_presidents": [],
            "persons_unknown_party": [],
            "persons_unknown_agency_in_role": [],
        },
    )

    result = _run(
        ["--registry-dir", str(registry_dir), "--report", str(stale), "--strict"]
    )

    assert result.returncode == 1
    assert "persons_unknown_agency_in_role" in result.stderr
    payload = json.loads(result.stdout)
    assert payload["report_source"] == "recomputed"


def test_unknown_agencies_fail_strict_when_using_report(tmp_path):
    bad = tmp_path / "bad_agency.json"
    _write_json(
        bad,
        {
            "missing_party_leaders": [],
            "missing_party_presidents": [],
            "persons_unknown_party": [],
            "persons_unknown_agency_in_role": [
                {"person_id": "p1", "organization": "missing-agency"}
            ],
        },
    )

    result = _run(["--report", str(bad), "--strict", "--use-report"])

    assert result.returncode == 1
    assert "persons_unknown_agency_in_role" in result.stderr


def test_unknown_parties_fail_strict_when_using_report(tmp_path):
    bad = tmp_path / "bad_party.json"
    _write_json(
        bad,
        {
            "missing_party_leaders": [],
            "missing_party_presidents": [],
            "persons_unknown_party": ["orphan-person"],
            "persons_unknown_agency_in_role": [],
        },
    )

    result = _run(["--report", str(bad), "--strict", "--use-report"])

    assert result.returncode == 1
    assert "persons_unknown_party" in result.stderr


def test_missing_leaders_within_tolerance_passes_when_using_report(tmp_path):
    rep = tmp_path / "tolerance.json"
    _write_json(
        rep,
        {
            "missing_party_leaders": ["p1", "p2"],
            "missing_party_presidents": [],
            "persons_unknown_party": [],
            "persons_unknown_agency_in_role": [],
        },
    )

    result = _run(
        [
            "--report",
            str(rep),
            "--strict",
            "--use-report",
            "--allow-leaders",
            "5",
            "--allow-presidents",
            "0",
        ]
    )

    assert result.returncode == 0, result.stderr


def test_missing_leaders_exceeding_tolerance_fails_when_using_report(tmp_path):
    rep = tmp_path / "exceed.json"
    _write_json(
        rep,
        {
            "missing_party_leaders": ["p1", "p2", "p3", "p4"],
            "missing_party_presidents": [],
            "persons_unknown_party": [],
            "persons_unknown_agency_in_role": [],
        },
    )

    result = _run(
        [
            "--report",
            str(rep),
            "--strict",
            "--use-report",
            "--allow-leaders",
            "2",
        ]
    )

    assert result.returncode == 1
    assert "missing_party_leaders" in result.stderr


def test_json_output_written_from_recomputed_registry(tmp_path):
    registry_dir = _registry(tmp_path)
    out = tmp_path / "summary.json"

    result = _run(["--registry-dir", str(registry_dir), "--json-output", str(out)])

    assert result.returncode == 0
    assert out.exists()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["report_source"] == "recomputed"
    assert "summary" in payload
    assert "hard_failures" in payload
    assert "tolerances" in payload


def test_write_report_persists_recomputed_gap_report(tmp_path):
    registry_dir = _registry(tmp_path)
    report_path = tmp_path / "gap-report.json"

    result = _run(
        ["--registry-dir", str(registry_dir), "--report", str(report_path), "--write-report"]
    )

    assert result.returncode == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["persons_unknown_agency_in_role"] == []
