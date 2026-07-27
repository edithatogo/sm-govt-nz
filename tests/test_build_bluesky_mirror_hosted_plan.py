from scripts.build_bluesky_mirror_hosted_plan import build_hosted_plan


def test_hosted_plan_uses_durable_evidence_and_leaves_rotation_external() -> None:
    plan = build_hosted_plan(
        {
            "live_posting_performed": False,
            "hosted_preflight": {"run_id": 3, "conclusion": "success", "posted": 0},
            "hosted_cleanup": {
                "run_id": 4,
                "conclusion": "success",
                "findings_valid": True,
                "reports_committed": ["acc", "courts"],
            },
        },
        {"hosted_success_run": 1},
        {
            "apply_requested": False,
            "mirror_id": "courts",
            "resumed": False,
            "status": "ready_to_resume",
        },
        {"external_action": "rotate", "rotation_verified": False},
        generated_at="fixed",
    )

    assert plan["summary"] == {
        "completed": 4,
        "external_action_required": 1,
        "pending": 1,
    }
    assert plan["global_invariants"]["live_posting_performed"] is False
    assert plan["stages"][-1]["status"] == "external_action_required"


def test_missing_evidence_remains_pending_and_rotation_can_complete() -> None:
    plan = build_hosted_plan(
        {},
        {},
        {},
        {"rotation_verified": True},
        generated_at="fixed",
    )

    assert plan["summary"] == {
        "completed": 1,
        "external_action_required": 0,
        "pending": 5,
    }


def test_applied_recovery_requires_explicit_resumed_terminal_evidence() -> None:
    common = ({}, {}, {"rotation_verified": True})
    completed = build_hosted_plan(
        common[0],
        common[1],
        {"apply_requested": True, "resumed": True, "status": "resumed"},
        common[2],
        generated_at="fixed",
    )
    ambiguous = build_hosted_plan(
        common[0],
        common[1],
        {"apply_requested": True, "resumed": False, "status": "resumed"},
        common[2],
        generated_at="fixed",
    )

    assert completed["stages"][1]["status"] == "completed"
    assert ambiguous["stages"][1]["status"] == "pending"


def test_successful_runs_do_not_override_failed_closed_evidence() -> None:
    plan = build_hosted_plan(
        {
            "hosted_preflight": {
                "conclusion": "success",
                "posted": 1,
            },
            "hosted_cleanup": {
                "conclusion": "success",
                "findings_valid": False,
                "run_id": 4,
            },
        },
        {},
        {},
        {"rotation_verified": True},
        generated_at="fixed",
    )

    stages = {stage["action"]: stage for stage in plan["stages"]}
    assert stages["credential_preflight"] == {
        "action": "credential_preflight",
        "posting_performed": True,
        "run_id": None,
        "status": "pending",
    }
    assert stages["cleanup_reconciliation"]["status"] == "external_action_required"
    assert stages["cleanup_reconciliation"]["findings_valid"] is False
    assert stages["cleanup_reconciliation"]["posting_performed"] is False
    assert plan["summary"]["external_action_required"] == 1


def test_completed_observation_closes_only_the_observation_stage() -> None:
    plan = build_hosted_plan(
        {},
        {},
        {},
        {"rotation_verified": False},
        {
            "complete": True,
            "deadline_at": "2026-08-03T09:15:55+00:00",
            "accepted_run_ids": [1, 2, 3, 4, 5, 6, 7],
            "missing_dates": [],
        },
        generated_at="fixed",
    )
    stages = {stage["action"]: stage for stage in plan["stages"]}
    assert stages["post_remediation_observation"]["status"] == "completed"
    assert stages["credential_rotation_and_revocation"]["status"] == "external_action_required"
