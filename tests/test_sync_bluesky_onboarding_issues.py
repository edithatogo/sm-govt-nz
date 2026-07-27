import copy

import pytest

from scripts import sync_bluesky_onboarding_issues as sync


def mirror(mirror_id: str, issue_number: int | None = None) -> dict:
    return {
        "mirror_id": mirror_id,
        "agency_name": mirror_id.title(),
        "environment": f"bluesky-mirror-{mirror_id}",
        "issue_number": issue_number,
        "evidence": [],
    }


def issue(number: int, title: str, body: str = "", state: str = "OPEN") -> dict:
    return {
        "number": number,
        "title": title,
        "body": body,
        "state": state,
        "url": f"https://github.com/example/repo/issues/{number}",
    }


def test_plan_is_read_only_and_classifies_existing_repair_and_proposed() -> None:
    registry = {
        "mirrors": [mirror("alpha", 11), mirror("beta"), mirror("gamma")],
        "onboarding_cohorts": {"cohort-01": 10, "cohort-02": 20},
    }
    original = copy.deepcopy(registry)
    remote = [
        issue(10, "[Cohort 01] Bluesky archive mirror onboarding"),
        issue(20, "[Cohort 02] Bluesky archive mirror onboarding"),
        issue(11, "[Onboarding] Bluesky archive mirror: Alpha", "Mirror ID: `alpha`"),
        issue(
            12,
            "[Onboarding] Bluesky archive mirror: Beta",
            "Mirror ID: `beta`",
            "CLOSED",
        ),
    ]

    plan = sync.build_issue_plan(registry, remote, parent=23, cohort_size=2, generated_at="fixed")

    assert registry == original
    assert plan["registry_write_performed"] is False
    assert plan["github_write_performed"] is False
    assert plan["summary"] == {
        "cohort_count": 2,
        "onboarding_count": 3,
        "existing": 1,
        "existing_closed": 0,
        "registry_repairs": 1,
        "proposed": 1,
        "hierarchy_repairs": 0,
        "blockers": 0,
    }
    states = {row["mirror_id"]: row["status"] for row in plan["onboarding"]}
    assert states == {
        "alpha": "existing",
        "beta": "registry_repair",
        "gamma": "proposed",
    }


def test_closed_registered_issue_is_preserved_without_recreation() -> None:
    registry = {"mirrors": [mirror("alpha", 11)], "onboarding_cohorts": {}}
    remote = [
        issue(
            11,
            "[Onboarding] Bluesky archive mirror: Alpha",
            "Mirror ID: `alpha`",
            "CLOSED",
        )
    ]
    plan = sync.build_issue_plan(registry, remote, parent=23, cohort_size=50, generated_at="fixed")
    assert plan["onboarding"][0]["status"] == "existing_closed"
    assert plan["summary"]["proposed"] == 0


def test_duplicate_and_stale_evidence_blocks_apply() -> None:
    registry = {
        "mirrors": [mirror("alpha", 99), mirror("beta")],
        "onboarding_cohorts": {},
    }
    remote = [
        issue(12, "First", "Mirror ID: `beta`"),
        issue(13, "Second", "Mirror ID: `beta`"),
    ]
    plan = sync.build_issue_plan(registry, remote, parent=23, cohort_size=50, generated_at="fixed")
    assert plan["summary"]["blockers"] == 2
    with pytest.raises(RuntimeError, match="blockers"):
        sync.apply_issue_plan(registry, plan, repo="example/repo", limit=5)


def test_apply_repairs_registry_and_creates_only_bounded_proposals(monkeypatch) -> None:
    registry = {
        "mirrors": [mirror("alpha"), mirror("beta")],
        "onboarding_cohorts": {"cohort-01": 10},
    }
    remote = [
        issue(10, "[Cohort 01] Bluesky archive mirror onboarding"),
        issue(11, "Alpha", "Mirror ID: `alpha`"),
    ]
    plan = sync.build_issue_plan(registry, remote, parent=23, cohort_size=50, generated_at="fixed")
    created: list[str] = []
    attached: list[tuple[int, int]] = []

    def create(_repo: str, title: str, _body: str) -> tuple[int, str]:
        created.append(title)
        return 12, "https://github.com/example/repo/issues/12"

    monkeypatch.setattr(sync, "_create_issue", create)
    monkeypatch.setattr(
        sync,
        "_attach_subissue",
        lambda _repo, parent, child: attached.append((parent, child)),
    )

    result = sync.apply_issue_plan(registry, plan, repo="example/repo", limit=1)

    assert registry["mirrors"][0]["issue_number"] == 11
    assert registry["mirrors"][1]["issue_number"] == 12
    assert result["apply_result"] == {
        "created_cohorts": 0,
        "created_onboarding": 1,
        "registry_repairs": 1,
        "hierarchy_repairs": 0,
        "limit": 1,
    }
    assert len(created) == 1
    assert attached == [(10, 12)]


@pytest.mark.parametrize("cohort_size", [0, 51])
def test_plan_rejects_invalid_cohort_sizes(cohort_size: int) -> None:
    with pytest.raises(ValueError, match="between 1 and 50"):
        sync.build_issue_plan(
            {"mirrors": []},
            [],
            parent=23,
            cohort_size=cohort_size,
            generated_at="fixed",
        )


def test_zero_limit_performs_no_github_writes(monkeypatch) -> None:
    registry = {"mirrors": [mirror("alpha")], "onboarding_cohorts": {}}
    plan = sync.build_issue_plan(registry, [], parent=23, cohort_size=50, generated_at="fixed")
    monkeypatch.setattr(
        sync,
        "_create_issue",
        lambda *_args, **_kwargs: pytest.fail("zero limit must not create issues"),
    )
    result = sync.apply_issue_plan(registry, plan, repo="example/repo", limit=0)
    assert result["apply_result"]["created_cohorts"] == 0
    assert result["apply_result"]["created_onboarding"] == 0
    assert result["github_write_performed"] is False


def test_apply_repairs_missing_hierarchy_after_interrupted_creation(monkeypatch) -> None:
    registry = {
        "mirrors": [mirror("alpha")],
        "onboarding_cohorts": {"cohort-01": 10},
    }
    remote = [
        issue(10, "[Cohort 01] Bluesky archive mirror onboarding"),
        issue(11, "Alpha", "Mirror ID: `alpha`"),
    ]
    plan = sync.build_issue_plan(
        registry,
        remote,
        parent=23,
        cohort_size=50,
        generated_at="fixed",
        cohort_memberships={10: set()},
    )
    attached: list[tuple[int, int]] = []
    monkeypatch.setattr(
        sync,
        "_attach_subissue",
        lambda _repo, parent, child: attached.append((parent, child)),
    )

    assert plan["summary"]["hierarchy_repairs"] == 1
    result = sync.apply_issue_plan(registry, plan, repo="example/repo", limit=0)
    assert attached == [(10, 11)]
    assert result["apply_result"]["hierarchy_repairs"] == 1
    assert registry["mirrors"][0]["issue_number"] == 11


def test_wrong_cohort_parent_is_a_blocker() -> None:
    registry = {
        "mirrors": [mirror("alpha", 11)],
        "onboarding_cohorts": {"cohort-01": 10},
    }
    remote = [
        issue(10, "[Cohort 01] Bluesky archive mirror onboarding"),
        issue(20, "[Cohort 02] Bluesky archive mirror onboarding"),
        issue(11, "Alpha", "Mirror ID: `alpha`"),
    ]
    plan = sync.build_issue_plan(
        registry,
        remote,
        parent=23,
        cohort_size=50,
        generated_at="fixed",
        cohort_memberships={10: set(), 20: {11}},
    )
    assert plan["onboarding"][0]["hierarchy_status"] == "wrong_parent"
    assert plan["summary"]["blockers"] == 1
