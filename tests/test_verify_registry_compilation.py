"""Unit tests for scripts/verify_registry_compilation.py."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from scripts.verify_registry_compilation import build_report, verify_registry


SAMPLE_JSON = [
    {
        "agency_id": "courts-of-nz",
        "name": "Courts of New Zealand",
        "type": "Judiciary",
        "portfolio": "Justice",
        "official_website": "https://www.courtsofnz.govt.nz",
        "status": "active",
        "parent_agency_id": None,
        "social_profiles": {
            "bluesky": {
                "handle": "courtsofnz.bsky.social",
                "url": "https://bsky.app/profile/courtsofnz.bsky.social",
                "status": "active",
            },
            "x": {
                "handle": "courtsofnz",
                "url": "https://twitter.com/courtsofnz",
                "status": "deactivated",
            },
        },
    },
    {
        "agency_id": "ministry-of-health",
        "name": "Ministry of Health",
        "type": "Ministry",
        "portfolio": "Health",
        "official_website": "https://www.health.govt.nz",
        "status": "active",
        "parent_agency_id": None,
        "social_profiles": {
            "bluesky": {
                "handle": "health.govt.nz",
                "url": "https://bsky.app/profile/health.govt.nz",
                "status": "active",
            },
        },
    },
]


def _build_db(data: list[dict], db_path: Path) -> None:
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute(
        """CREATE TABLE agencies (
            agency_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT,
            portfolio TEXT,
            official_website TEXT,
            status TEXT,
            parent_agency_id TEXT,
            domain TEXT
        )"""
    )
    cursor.execute(
        """CREATE TABLE social_profiles (
            profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
            agency_id TEXT NOT NULL,
            platform TEXT NOT NULL,
            handle TEXT NOT NULL,
            url TEXT NOT NULL,
            status TEXT NOT NULL,
            deactivated_at TEXT,
            reason TEXT,
            alternative_url TEXT,
            FOREIGN KEY (agency_id) REFERENCES agencies (agency_id)
        )"""
    )
    for item in data:
        cursor.execute(
            """INSERT INTO agencies (
                agency_id, name, type, portfolio, official_website, status, parent_agency_id, domain
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                item["agency_id"],
                item["name"],
                item.get("type"),
                item.get("portfolio"),
                item["official_website"],
                item["status"],
                item.get("parent_agency_id"),
                item["official_website"].split("//", 1)[-1].removeprefix("www."),
            ),
        )
        for platform, profile in item.get("social_profiles", {}).items():
            cursor.execute(
                """INSERT INTO social_profiles (
                    agency_id, platform, handle, url, status, deactivated_at, reason, alternative_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    item["agency_id"],
                    platform,
                    profile["handle"],
                    profile["url"],
                    profile["status"],
                    profile.get("deactivated_at"),
                    profile.get("reason"),
                    profile.get("alternative_url"),
                ),
            )
    conn.commit()
    conn.close()


def _write_json(path: Path, data: list[dict]) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def test_verify_registry_ok(tmp_path: Path) -> None:
    json_path = tmp_path / "directory.json"
    db_path = tmp_path / "directory.db"
    _write_json(json_path, SAMPLE_JSON)
    _build_db(SAMPLE_JSON, db_path)

    result = verify_registry(json_path=str(json_path), db_path=str(db_path))

    assert result.ok is True
    assert result.status == "ok"
    assert result.json_entry_count == 2
    assert result.json_profile_count == 3
    assert result.db_agency_count == 2
    assert result.db_profile_count == 3
    assert result.mismatches == []


def test_verify_registry_json_missing() -> None:
    result = verify_registry(json_path="/missing/input.json", db_path="/missing/db.db")

    assert result.ok is False
    assert result.status == "json_missing"
    assert result.json_exists is False


def test_verify_registry_db_missing(tmp_path: Path) -> None:
    json_path = tmp_path / "directory.json"
    _write_json(json_path, SAMPLE_JSON)

    result = verify_registry(json_path=str(json_path), db_path=str(tmp_path / "missing.db"))

    assert result.ok is False
    assert result.status == "db_missing"
    assert result.json_exists is True
    assert result.db_exists is False


def test_verify_registry_row_count_mismatch(tmp_path: Path) -> None:
    json_path = tmp_path / "directory.json"
    db_path = tmp_path / "directory.db"
    _write_json(json_path, SAMPLE_JSON)
    _build_db([SAMPLE_JSON[0]], db_path)

    result = verify_registry(json_path=str(json_path), db_path=str(db_path))

    assert result.ok is False
    assert result.status == "row_count_mismatch"
    assert any(m.field == "row_counts" for m in result.mismatches)


def test_build_report_contains_validation_payload(tmp_path: Path) -> None:
    result = verify_registry(json_path=str(tmp_path / "missing.json"), db_path=str(tmp_path / "missing.db"))
    report = build_report(result)

    assert report["tool"] == "verify_registry_compilation"
    assert report["validation"]["status"] == "json_missing"
