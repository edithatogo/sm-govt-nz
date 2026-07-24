from pathlib import Path

import pytest

from src.bluesky_handle_lifecycle import (
    custom_domain_readiness_plan,
    find_stale_handle_references,
    migration_plan,
    retired_handle_report,
    validate_abbreviation_registry,
)


def abbreviation_registry(**overrides):
    entry = {
        "agency_id": "accident-compensation-corporation",
        "canonical_name": "Accident Compensation Corporation",
        "organisation_abbreviation": "acc",
        "abbreviation_status": "approved",
        "abbreviation_approved_at": "2026-07-24",
        "abbreviation_approval_evidence": "operator-approved migration",
        "jurisdiction": "nz",
        "approved_handle": "acc-nz-arc.bsky.social",
        "account_did": "did:plc:vxltrdhni2dfsm4actryhj4n",
        "retired_handles": ["accident-comp-arc.bsky.social"],
    }
    entry.update(overrides)
    return {
        "schema_version": 1,
        "abbreviation_policy": {
            "approval_required": True,
            "automatic_inference_allowed": False,
        },
        "custom_domain_migration": {
            "enabled": False,
            "automatic_migration_allowed": False,
            "required_evidence": ["operator_approval"],
        },
        "entries": [entry],
    }


def test_abbreviation_registry_enforces_handle_and_did_contract() -> None:
    validate_abbreviation_registry(abbreviation_registry())
    with pytest.raises(ValueError, match="does not match policy"):
        validate_abbreviation_registry(
            abbreviation_registry(approved_handle="accident-comp-archive.bsky.social")
        )
    with pytest.raises(ValueError, match="Invalid account DID"):
        validate_abbreviation_registry(abbreviation_registry(account_did="invalid"))
    with pytest.raises(ValueError, match="also retired"):
        validate_abbreviation_registry(
            abbreviation_registry(retired_handles=["acc-nz-arc.bsky.social"])
        )
    with pytest.raises(ValueError, match="not approved"):
        validate_abbreviation_registry(
            abbreviation_registry(abbreviation_status="proposed")
        )


def test_migration_plan_is_did_first_and_nonsecret() -> None:
    mirror = {
        "mirror_id": "accident-compensation-corporation",
        "agency_id": "accident-compensation-corporation",
        "environment": "bluesky-mirror-accident-compensation-corporation",
    }
    entry = abbreviation_registry()["entries"][0]
    plan = migration_plan(
        mirror, entry, old_handle="accident-comp-arc.bsky.social"
    )
    assert plan["account_did"] == entry["account_did"]
    assert plan["new_handle"] == "acc-nz-arc.bsky.social"
    assert "update_github_environment_handle" in plan["steps"]
    assert "password" not in str(plan).casefold()


def test_stale_link_scan_is_bounded_and_excludes_archives(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "mirror.md").write_text(
        "See accident-comp-arc.bsky.social\n", encoding="utf-8"
    )
    (tmp_path / "historical_archive_raw").mkdir()
    (tmp_path / "historical_archive_raw" / "evidence.json").write_text(
        '{"handle":"accident-comp-arc.bsky.social"}\n', encoding="utf-8"
    )
    matches = find_stale_handle_references(
        tmp_path, ["accident-comp-arc.bsky.social"]
    )
    assert matches == [
        {
            "path": "docs/mirror.md",
            "line": 1,
            "handle": "accident-comp-arc.bsky.social",
            "classification": "actionable_stale_reference",
            "actionable": True,
        }
    ]


def test_retired_handle_monitoring_detects_reuse() -> None:
    registry = abbreviation_registry()

    def missing(_handle: str) -> str:
        raise __import__("urllib.error").error.HTTPError(
            "https://example.invalid", 400, "missing", {}, None
        )

    healthy = retired_handle_report(registry, resolver=missing)
    assert healthy["actionable_count"] == 0
    reused = retired_handle_report(
        registry, resolver=lambda _handle: "did:plc:aaaaaaaaaaaaaaaaaaaaaaaa"
    )
    assert reused["actionable_count"] == 1
    assert reused["results"][0]["classification"] == "unexpected_registration"


def test_custom_domain_plan_is_non_operative() -> None:
    plan = custom_domain_readiness_plan(
        abbreviation_registry(), "accident-compensation-corporation"
    )
    assert plan["enabled"] is False
    assert plan["automatic_migration_allowed"] is False
    assert plan["state"] == "deferred_pending_operator_approval"
