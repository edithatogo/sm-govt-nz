import copy
import json
from pathlib import Path

from scripts.build_bluesky_mirror_readiness import (
    build_account_packet,
    build_candidate_readiness_inventory,
)
from src.bluesky_mirror_programme import load_archive_records, load_registry


def load_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def handle_readiness() -> dict:
    return {
        "probes": [
            {
                "handle": "electoral-commission-nz-arc.bsky.social",
                "state": "unregistered",
            },
            {
                "handle": "electoral-commission-nz-arc-2.bsky.social",
                "state": "unregistered",
            },
        ]
    }


def environment_readiness() -> dict:
    return {
        "name": "bluesky-mirror-electoral-commission",
        "exists": True,
        "secrets_configured": False,
        "deployment_branch_policy": {
            "protected_branches": False,
            "custom_branch_policies": True,
        },
        "allowed_branches": ["master"],
    }


def test_full_inventory_is_untruncated_and_reconciles_every_candidate() -> None:
    inventory = build_candidate_readiness_inventory(
        load_registry(), "historical_archive_normalized", generated_at="fixed"
    )
    rows = inventory["candidates"]
    electoral = next(row for row in rows if row["mirror_id"] == "electoral-commission")

    assert inventory["candidate_count"] == 240
    assert inventory["eligible_candidate_count"] == 136
    assert inventory["zero_eligible_candidate_count"] == 104
    assert inventory["truncated"] == 0
    assert len(rows) == len({row["mirror_id"] for row in rows}) == 240
    assert electoral["scanned_records"] == 3
    assert electoral["accepted_contract_records"] == 1
    assert electoral["eligible_backlog"] == 1
    assert electoral["rejection_reason_counts"] == {
        "source_id_not_allowed": 1,
        "source_kind_not_mirrorable": 1,
    }
    assert all(row["terminal"] is False for row in rows)


def test_electoral_packet_is_source_exact_secret_free_and_operator_gated() -> None:
    registry = load_registry()
    inventory = load_json("conductor/bluesky_mirror_candidate_readiness.json")
    packet = build_account_packet(
        registry,
        inventory,
        load_json("config/bluesky_mirror_abbreviations.json"),
        handle_readiness(),
        environment_readiness(),
        "electoral-commission",
        generated_at="fixed",
    )
    account = next(row for row in registry["mirrors"] if row["mirror_id"] == "electoral-commission")

    assert packet["pre_registration_ready"] is True
    assert packet["status"] == "operator_registration_required"
    assert packet["source_contract"]["source_ids"] == account["source_ids"]
    assert packet["source_contract"]["source_platforms"] == account["source_platforms"]
    assert packet["source_contract"]["source_urls"] == account["source_urls"]
    assert packet["secret_values_recorded"] is False
    assert "@gmail.com" not in json.dumps(packet).casefold()
    assert packet["gates"]["account_registered"] is False
    assert packet["gates"]["backfill_approved"] is False


def test_packet_fails_closed_when_environment_evidence_is_missing() -> None:
    inventory = load_json("conductor/bluesky_mirror_candidate_readiness.json")
    environment = copy.deepcopy(environment_readiness())
    environment["exists"] = False
    packet = build_account_packet(
        load_registry(),
        inventory,
        load_json("config/bluesky_mirror_abbreviations.json"),
        handle_readiness(),
        environment,
        "electoral-commission",
        generated_at="fixed",
    )

    assert packet["pre_registration_ready"] is False
    assert packet["status"] == "evidence_incomplete"


def test_per_account_eligibility_ignores_other_agencies(tmp_path: Path) -> None:
    archive_root = tmp_path / "archive"
    archive_root.mkdir()
    records = [
        {"agency_id": "electoral-commission", "record_id": "electoral"},
        {"agency_id": "another-agency", "record_id": "other"},
    ]
    (archive_root / "records.jsonl").write_text(
        "\n".join(json.dumps(record) for record in records) + "\n",
        encoding="utf-8",
    )
    registry = load_registry()
    account = next(row for row in registry["mirrors"] if row["mirror_id"] == "electoral-commission")
    report = tmp_path / "eligibility.json"

    load_archive_records(account, archive_root, eligibility_report_path=report)
    payload = json.loads(report.read_text(encoding="utf-8"))

    assert payload["scanned"] == 1
    assert payload["rejected"] == 1
    assert payload["rejection_reason_counts"] == {"missing_source_id": 1}
