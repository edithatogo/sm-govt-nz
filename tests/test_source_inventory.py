import json

import pytest

from src.source_inventory import load_source_inventory


def test_load_courts_nz_source_inventory():
    inventory = load_source_inventory()

    assert inventory["agency_id"] == "courts-nz"
    assert inventory["archive_only"] is True
    assert {contract["source_platform"] for contract in inventory["contracts"]} == {
        "bluesky",
        "linkedin",
        "x",
        "courtsofnz.govt.nz",
        "email",
    }
    assert inventory["dataset_outputs"]["hugging_face"]["enabled"] is True
    assert inventory["dataset_outputs"]["zenodo"]["enabled"] is True
    assert inventory["phase_review_contract"]["commit_after_each_task"] is True


def test_source_inventory_requires_archive_only(tmp_path):
    inventory_path = tmp_path / "sources.json"
    inventory_path.write_text(
        json.dumps(
            {
                "agency_id": "courts-nz",
                "agency_name": "Courts of New Zealand",
                "archive_only": False,
                "contracts": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="archive_only=true"):
        load_source_inventory(inventory_path)


def test_source_inventory_rejects_invalid_health_status(tmp_path):
    inventory = load_source_inventory()
    inventory["contracts"][0]["status"] = "unknown"
    inventory_path = tmp_path / "sources.json"
    inventory_path.write_text(json.dumps(inventory), encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid source health status"):
        load_source_inventory(inventory_path)
