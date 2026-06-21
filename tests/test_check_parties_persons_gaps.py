"""Tests for scripts/check_parties_persons_gaps.py.

Validates the strict CI gate helper script: argument parsing, JSON
output, exit codes, and tolerance handling.
"""

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


def test_help_exits_zero():
    result = _run(["--help"])
    assert result.returncode == 0
    assert "--report" in result.stdout


def test_missing_report_passes_when_not_strict():
    missing = Path("conductor/_missing_for_test.json")
    if missing.exists():
        missing.unlink()
    result = _run(["--report", str(missing)])
    assert result.returncode == 0


def test_missing_report_fails_when_strict():
    missing = Path("conductor/_missing_for_test.json")
    if missing.exists():
        missing.unlink()
    result = _run(["--report", str(missing), "--strict"])
    assert result.returncode == 1


def test_zero_gaps_passes_strict():
    empty = Path("conductor/_empty_for_test.json")
    empty.write_text(
        json.dumps(
            {
                "missing_party_leaders": [],
                "missing_party_presidents": [],
                "persons_unknown_party": [],
                "persons_unknown_agency_in_role": [],
            }
        ),
        encoding="utf-8",
    )
    try:
        result = _run(["--report", str(empty), "--strict"])
        assert result.returncode == 0, result.stderr
    finally:
        empty.unlink()


def test_unknown_agencies_fail_strict():
    bad = Path("conductor/_bad_agency.json")
    bad.write_text(
        json.dumps(
            {
                "missing_party_leaders": [],
                "missing_party_presidents": [],
                "persons_unknown_party": [],
                "persons_unknown_agency_in_role": [
                    {"person_id": "p1", "organization": "missing-agency"}
                ],
            }
        ),
        encoding="utf-8",
    )
    try:
        result = _run(["--report", str(bad), "--strict"])
        assert result.returncode == 1
        assert "persons_unknown_agency_in_role" in result.stderr
    finally:
        bad.unlink()


def test_unknown_parties_fail_strict():
    bad = Path("conductor/_bad_party.json")
    bad.write_text(
        json.dumps(
            {
                "missing_party_leaders": [],
                "missing_party_presidents": [],
                "persons_unknown_party": ["orphan-person"],
                "persons_unknown_agency_in_role": [],
            }
        ),
        encoding="utf-8",
    )
    try:
        result = _run(["--report", str(bad), "--strict"])
        assert result.returncode == 1
        assert "persons_unknown_party" in result.stderr
    finally:
        bad.unlink()


def test_missing_leaders_within_tolerance_passes():
    rep = Path("conductor/_tolerance.json")
    rep.write_text(
        json.dumps(
            {
                "missing_party_leaders": ["p1", "p2"],
                "missing_party_presidents": [],
                "persons_unknown_party": [],
                "persons_unknown_agency_in_role": [],
            }
        ),
        encoding="utf-8",
    )
    try:
        result = _run(
            [
                "--report",
                str(rep),
                "--strict",
                "--allow-leaders",
                "5",
                "--allow-presidents",
                "0",
            ]
        )
        assert result.returncode == 0, result.stderr
    finally:
        rep.unlink()


def test_missing_leaders_exceeding_tolerance_fails():
    rep = Path("conductor/_exceed.json")
    rep.write_text(
        json.dumps(
            {
                "missing_party_leaders": ["p1", "p2", "p3", "p4"],
                "missing_party_presidents": [],
                "persons_unknown_party": [],
                "persons_unknown_agency_in_role": [],
            }
        ),
        encoding="utf-8",
    )
    try:
        result = _run(
            [
                "--report",
                str(rep),
                "--strict",
                "--allow-leaders",
                "2",
            ]
        )
        assert result.returncode == 1
        assert "missing_party_leaders" in result.stderr
    finally:
        rep.unlink()


def test_json_output_written(tmp_path):
    rep = Path("conductor/_jsonout.json")
    rep.write_text(
        json.dumps(
            {
                "missing_party_leaders": [],
                "missing_party_presidents": [],
                "persons_unknown_party": [],
                "persons_unknown_agency_in_role": [],
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "summary.json"
    try:
        result = _run(["--report", str(rep), "--json-output", str(out)])
        assert result.returncode == 0
        assert out.exists()
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert "summary" in payload
        assert "hard_failures" in payload
        assert "tolerances" in payload
    finally:
        rep.unlink()
