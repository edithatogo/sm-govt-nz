import pytest

from scripts.manage_bluesky_mirror_handle import (
    _verification_identity,
    candidate_availability_report,
)


def test_verification_identity_uses_approved_lifecycle_entry() -> None:
    mirror = {"agency_id": "agency", "mirror_id": "agency"}
    entries = [
        {
            "agency_id": "agency",
            "approved_handle": "agency-nz-arc.bsky.social",
            "account_did": "did:plc:approved",
        }
    ]

    assert _verification_identity(mirror, entries) == (
        "agency-nz-arc.bsky.social",
        "did:plc:approved",
    )


def test_verification_identity_allows_evidenced_legacy_canary() -> None:
    mirror = {
        "agency_id": "courts-of-nz",
        "mirror_id": "courts-of-nz",
        "handle_policy_version": 0,
        "legacy_handle_exception": "Pre-programme canary.",
        "handle": "mirnzcourts.bsky.social",
        "account_did": "did:plc:courts",
    }

    assert _verification_identity(mirror, []) == (
        "mirnzcourts.bsky.social",
        "did:plc:courts",
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {},
        {"handle_policy_version": 0},
        {"handle_policy_version": 0, "legacy_handle_exception": "approved"},
    ],
)
def test_verification_identity_rejects_unevidenced_legacy_rows(
    overrides: dict[str, object],
) -> None:
    mirror = {
        "agency_id": "courts-of-nz",
        "mirror_id": "courts-of-nz",
        **overrides,
    }

    with pytest.raises(ValueError):
        _verification_identity(mirror, [])


def test_candidate_availability_report_preserves_order_and_requires_all_unregistered() -> None:
    mirror = {
        "mirror_id": "agency",
        "handle_candidates": [
            "agency-nz-arc.bsky.social",
            "agency-nz-arc-2.bsky.social",
        ],
    }
    states = {
        "agency-nz-arc.bsky.social": "unregistered",
        "agency-nz-arc-2.bsky.social": "registered",
    }
    report = candidate_availability_report(
        mirror,
        probe=lambda handle: {"handle": handle, "state": states[handle], "did": ""},
        checked_at="fixed",
    )
    assert [row["handle"] for row in report["probes"]] == mirror["handle_candidates"]
    assert report["all_unregistered"] is False
    assert report["secret_values_recorded"] is False
