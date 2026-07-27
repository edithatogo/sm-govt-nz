from scripts.build_bluesky_mirror_hosted_plan import build_hosted_plan


def test_hosted_plan_uses_durable_evidence_and_leaves_rotation_external() -> None:
    plan = build_hosted_plan(
        {
            "live_posting_performed": False,
            "hosted_preflight": {"run_id": 3, "conclusion": "success", "posted": 0},
            "hosted_cleanup": {
                "run_id": 4,
                "conclusion": "success",
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
        "pending": 0,
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
        "pending": 4,
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
