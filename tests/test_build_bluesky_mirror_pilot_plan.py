import json

from scripts.build_bluesky_mirror_pilot_plan import build_pilot_plan, render_markdown


def mirror(agency_id, *, issue=1, source_id="source", role="agency_mirror"):
    return {
        "account_role": role,
        "agency_id": agency_id,
        "agency_name": agency_id.title(),
        "enabled": False,
        "environment": f"bluesky-mirror-{agency_id}",
        "handle_candidates": [f"{agency_id}-nz-arc.bsky.social"],
        "issue_number": issue,
        "lifecycle_state": "candidate",
        "mirror_id": agency_id,
        "source_ids": [source_id] if source_id else [],
        "source_urls": [],
    }


def record(record_id, source_id, platform="x"):
    return {
        "cross_source_ids": {"source_id": source_id},
        "record_id": record_id,
        "source_platform": platform,
    }


def test_selects_two_smallest_backlogs_then_agency_id() -> None:
    registry = {
        "mirrors": [
            mirror("charlie", source_id="c"),
            mirror("alpha", source_id="a"),
            mirror("bravo", source_id="b"),
        ]
    }
    records = [
        record("a1", "a"),
        record("b1", "b"),
        record("c1", "c"),
        record("c2", "c"),
    ]

    plan = build_pilot_plan(registry, records, generated_at="fixed")

    assert [row["mirror_id"] for row in plan["selected"]] == ["alpha", "bravo"]
    assert plan["summary"] == {
        "candidate_count": 3,
        "eligible_count": 3,
        "selected_count": 2,
    }


def test_fails_closed_without_issue_sources_or_archived_records() -> None:
    registry = {
        "mirrors": [
            mirror("no-issue", issue=None, source_id="one"),
            mirror("no-source", source_id=""),
            mirror("no-records", source_id="missing"),
            mirror("index", source_id="index", role="index"),
        ]
    }

    plan = build_pilot_plan(registry, [record("one", "one")], generated_at="fixed")

    assert plan["selected"] == []
    assert plan["eligible_candidates"] == []
    assert plan["blocker_counts"] == {
        "archived_records_missing": 2,
        "onboarding_issue_missing": 1,
        "registered_sources_missing": 1,
    }


def test_matches_normalized_source_urls_and_renders_operator_summary() -> None:
    row = mirror("agency", source_id="missing")
    row["source_urls"] = ["https://example.test/profile/"]
    plan = build_pilot_plan(
        {"mirrors": [row]},
        [
            {
                "record_id": "r1",
                "source_platform": "facebook",
                "source_url": "https://example.test/profile",
            }
        ],
        generated_at="fixed",
    )

    assert plan["selected"][0]["archive_record_count"] == 1
    assert "| yes | Agency | `agency` | 1 | 1 |  |" in render_markdown(plan)
    json.dumps(plan)
