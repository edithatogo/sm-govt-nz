from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.add_person_record import append_person_records


def _write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _registry(tmp_path: Path) -> Path:
    registry_dir = tmp_path / "registry"
    registry_dir.mkdir()
    _write_json(
        registry_dir / "schema_persons.json",
        json.loads(Path("registry/schema_persons.json").read_text(encoding="utf-8")),
    )
    _write_json(
        registry_dir / "government_directory.json",
        [
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
        registry_dir / "parties.json",
        [
            {
                "party_id": "example-party",
                "name": "Example Party",
                "status": "active",
            }
        ],
    )
    _write_json(
        registry_dir / "persons.json",
        [
            {
                "person_id": "existing-person",
                "full_name": "Existing Person",
                "party_id": "example-party",
                "roles": [
                    {
                        "role_id": "existing-role",
                        "title": "Existing Role",
                        "organization": "nz-parliament",
                        "category": "mp",
                        "is_current": True,
                    }
                ],
            }
        ],
    )
    return registry_dir


def _person(person_id: str = "new-person") -> dict:
    return {
        "person_id": person_id,
        "full_name": "New Person",
        "party_id": "example-party",
        "roles": [
            {
                "role_id": f"{person_id}-role",
                "title": "New Role",
                "organization": "nz-parliament",
                "category": "mp",
                "is_current": True,
            }
        ],
    }


def test_append_person_records_writes_valid_record(tmp_path):
    registry_dir = _registry(tmp_path)
    input_path = tmp_path / "person.json"
    _write_json(input_path, _person())

    result = append_person_records(input_path=input_path, registry_dir=registry_dir)

    persons = json.loads((registry_dir / "persons.json").read_text(encoding="utf-8"))
    assert result["wrote"] is True
    assert result["existing_count"] == 1
    assert result["result_count"] == 2
    assert [person["person_id"] for person in persons] == [
        "existing-person",
        "new-person",
    ]


def test_append_person_records_dry_run_does_not_write(tmp_path):
    registry_dir = _registry(tmp_path)
    input_path = tmp_path / "person.json"
    _write_json(input_path, _person())

    result = append_person_records(
        input_path=input_path, registry_dir=registry_dir, dry_run=True
    )

    persons = json.loads((registry_dir / "persons.json").read_text(encoding="utf-8"))
    assert result["wrote"] is False
    assert len(persons) == 1


def test_append_person_records_rejects_existing_duplicate(tmp_path):
    registry_dir = _registry(tmp_path)
    input_path = tmp_path / "person.json"
    _write_json(input_path, _person("existing-person"))

    try:
        append_person_records(input_path=input_path, registry_dir=registry_dir)
    except ValueError as exc:
        assert "already exist" in str(exc)
    else:
        raise AssertionError("expected duplicate person_id to fail")


def test_append_person_records_rejects_duplicate_ids_in_input(tmp_path):
    registry_dir = _registry(tmp_path)
    input_path = tmp_path / "people.json"
    _write_json(input_path, [_person("dup-person"), _person("dup-person")])

    try:
        append_person_records(input_path=input_path, registry_dir=registry_dir)
    except ValueError as exc:
        assert "duplicate person_id values in input" in str(exc)
    else:
        raise AssertionError("expected duplicate input person_id to fail")


def test_append_person_records_rejects_unknown_role_organization(tmp_path):
    registry_dir = _registry(tmp_path)
    input_path = tmp_path / "person.json"
    person = _person()
    person["roles"][0]["organization"] = "missing-agency"
    _write_json(input_path, person)

    try:
        append_person_records(input_path=input_path, registry_dir=registry_dir)
    except ValueError as exc:
        message = str(exc)
        assert "reference integrity failed" in message
        assert "missing-agency" in message
    else:
        raise AssertionError("expected unknown role organization to fail")


def test_append_person_records_rejects_schema_invalid_input(tmp_path):
    registry_dir = _registry(tmp_path)
    input_path = tmp_path / "person.json"
    _write_json(input_path, {"person_id": "invalid-person", "full_name": "Invalid"})

    try:
        append_person_records(input_path=input_path, registry_dir=registry_dir)
    except ValueError as exc:
        assert "schema validation failed" in str(exc)
    else:
        raise AssertionError("expected schema invalid record to fail")


def test_append_person_records_rejects_invalid_evidence_metadata(tmp_path):
    registry_dir = _registry(tmp_path)
    input_path = tmp_path / "person.json"
    person = _person()
    person["social_profiles"] = {
        "x": {
            "handle": "NewPerson",
            "url": "https://x.com/NewPerson",
            "status": "active",
            "evidence": {
                "source_url": "https://example.govt.nz/new-person",
                "source_type": "rumour",
                "captured_at": "2026-06-22",
            },
        }
    }
    _write_json(input_path, person)

    try:
        append_person_records(input_path=input_path, registry_dir=registry_dir)
    except ValueError as exc:
        assert "schema validation failed" in str(exc)
    else:
        raise AssertionError("expected invalid evidence metadata to fail")


def test_add_person_record_cli_validate_only(tmp_path):
    registry_dir = _registry(tmp_path)
    input_path = tmp_path / "person.json"
    _write_json(input_path, _person())

    result = subprocess.run(
        [
            sys.executable,
            "scripts/add_person_record.py",
            "--registry-dir",
            str(registry_dir),
            "--input",
            str(input_path),
            "--validate-only",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert '"wrote": false' in result.stdout
