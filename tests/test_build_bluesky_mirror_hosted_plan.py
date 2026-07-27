from scripts.build_bluesky_mirror_hosted_plan import build_hosted_plan


def test_hosted_plan_is_fail_closed_and_evidence_driven() -> None:
    plan = build_hosted_plan(
        {
            "live_posting_performed": False,
            "hosted_preflight": {
                "run_id": 10,
                "conclusion": "success",
                "posted": 0,
            },
            "hosted_cleanup": {
                "run_id": 11,
                "conclusion": "success",
                "findings_valid": False,
                "reports_committed": ["agency"],
            },
        },
        {"hosted_success_run": 12},
        {
            "mirror_id": "agency",
            "apply_requested": True,
            "resumed": True,
            "status": "resumed",
        },
        {
            "rotation_verification": "unverified",
            "external_action": "Rotate the credential.",
        },
        generated_at="2026-07-27T00:00:00+00:00",
    )

    assert plan["schema_version"] == 2
    assert plan["global_invariants"]["live_posting_allowed"] is False
    assert plan["global_invariants"]["destructive_cleanup_allowed"] is False
    assert plan["summary"] == {
        "completed": 3,
        "external_action_required": 1,
        "pending": 1,
    }
    stages = {stage["action"]: stage for stage in plan["stages"]}
    assert stages["cleanup_reconciliation"]["status"] == "pending"
    assert stages["credential_rotation_and_revocation"]["status"] == (
        "external_action_required"
    )


def test_hosted_plan_requires_zero_post_preflight_and_verified_rotation() -> None:
    plan = build_hosted_plan(
        {
            "hosted_preflight": {
                "conclusion": "success",
                "posted": 1,
            },
            "hosted_cleanup": {
                "conclusion": "success",
                "findings_valid": True,
            },
        },
        {},
        {},
        {"rotation_verification": "verified"},
        generated_at="2026-07-27T00:00:00+00:00",
    )

    stages = {stage["action"]: stage for stage in plan["stages"]}
    assert stages["credential_preflight"]["status"] == "pending"
    assert stages["cleanup_reconciliation"]["status"] == "completed"
    assert stages["credential_rotation_and_revocation"]["status"] == "completed"
