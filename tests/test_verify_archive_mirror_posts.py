import json

from scripts.verify_archive_mirror_posts import (
    reconcile_programme_audit,
    result_exit_code,
    verify_archive_mirror_posts,
)


def test_verify_archive_mirror_posts_checks_sampled_uris(tmp_path) -> None:
    state_path = tmp_path / "archive_mirror_state.json"
    write_state(state_path)

    result = verify_archive_mirror_posts(
        state_path=state_path,
        limit=1,
        client=FakePostClient(["at://did:plc:mirror/app.bsky.feed.post/second"]),
    )

    assert result == {
        "checked": 1,
        "failures": [],
        "target": "bluesky",
        "valid": True,
    }


def test_verify_archive_mirror_posts_reports_missing_public_post(tmp_path) -> None:
    state_path = tmp_path / "archive_mirror_state.json"
    write_state(state_path)

    result = verify_archive_mirror_posts(
        state_path=state_path,
        limit=1,
        client=FakePostClient([]),
    )

    assert result["valid"] is False
    assert result["failures"] == [
        {
            "mirror_url": "https://bsky.app/profile/did:plc:mirror/post/second",
            "record_id": "x:2",
            "uri": "at://did:plc:mirror/app.bsky.feed.post/second",
            "valid": False,
        }
    ]


def write_state(path) -> None:
    path.write_text(
        json.dumps(
            {
                "posted_records": {
                    "bluesky": {
                        "x:CourtsofNZ": [
                            {
                                "detail": "at://did:plc:mirror/app.bsky.feed.post/first",
                                "mirror_url": "https://bsky.app/profile/did:plc:mirror/post/first",
                                "record_id": "x:1",
                            },
                            {
                                "detail": "at://did:plc:mirror/app.bsky.feed.post/second",
                                "mirror_url": "https://bsky.app/profile/did:plc:mirror/post/second",
                                "record_id": "x:2",
                            },
                        ]
                    }
                }
            }
        ),
        encoding="utf-8",
    )


class FakePostClient:
    def __init__(self, uris: list[str]) -> None:
        self.uris = uris

    def fetch_posts(self, uris: list[str]):
        return [{"uri": uri} for uri in self.uris if uri in uris]


def test_acc_incident_sequence_generates_exact_uri_cleanup_packet(tmp_path) -> None:
    registry = tmp_path / "registry.json"
    registry.write_text(
        json.dumps(
            {
                "mirrors": [
                    {
                        "mirror_id": "accident-compensation-corporation",
                        "handle": "acc-nz-arc.bsky.social",
                        "source_ids": ["acc-linkedin"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    audit = tmp_path / "audit.jsonl"
    audit.write_text(
        "\n".join(
            json.dumps(row)
            for row in [
                {
                    "mirror_id": "accident-compensation-corporation",
                    "record_id": "youtube:old",
                    "rendered_hash": "same",
                    "source_id": "",
                    "uri": "at://did:plc:acc/app.bsky.feed.post/one",
                },
                {
                    "mirror_id": "accident-compensation-corporation",
                    "record_id": "youtube:old",
                    "rendered_hash": "same",
                    "source_id": "",
                    "uri": "at://did:plc:acc/app.bsky.feed.post/two",
                },
                {
                    "mirror_id": "accident-compensation-corporation",
                    "record_id": "linkedin:new",
                    "rendered_hash": "linkedin",
                    "source_id": "acc-linkedin",
                    "uri": "at://did:plc:acc/app.bsky.feed.post/three",
                },
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    client = FakeProgrammeClient(
        visible=[
            "at://did:plc:acc/app.bsky.feed.post/one",
            "at://did:plc:acc/app.bsky.feed.post/two",
            "at://did:plc:acc/app.bsky.feed.post/three",
        ]
    )

    result = reconcile_programme_audit(
        registry_path=registry,
        mirror_id="accident-compensation-corporation",
        audit_paths=[audit],
        client=client,
    )

    assert len(result["duplicates"]) == 1
    assert len(result["excluded_sources"]) == 2
    assert result["cleanup_approval_packet"]["destructive_action_performed"] is False
    assert all(
        item["requires_exact_uri_approval"]
        for item in result["cleanup_approval_packet"]["candidates"]
    )


def test_cleanup_report_classifies_missing_audit_and_deleted_posts(tmp_path) -> None:
    registry = tmp_path / "registry.json"
    registry.write_text(
        json.dumps(
            {
                "mirrors": [
                    {
                        "mirror_id": "agency",
                        "handle": "agency.bsky.social",
                        "source_ids": ["source"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    audit = tmp_path / "audit.jsonl"
    audit.write_text(
        json.dumps(
            {
                "mirror_id": "agency",
                "record_id": "r1",
                "rendered_hash": "hash",
                "source_id": "source",
                "uri": "at://did:plc:a/app.bsky.feed.post/deleted",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    client = FakeProgrammeClient(
        visible=[],
        feed=["at://did:plc:a/app.bsky.feed.post/untracked"],
    )

    result = reconcile_programme_audit(
        registry_path=registry,
        mirror_id="agency",
        audit_paths=[audit],
        client=client,
    )

    assert result["deleted_or_missing"][0]["uri"].endswith("/deleted")
    assert result["missing_audit"][0]["uri"].endswith("/untracked")


def test_reconciliation_findings_remain_strict_unless_report_only() -> None:
    result = {"valid": False}

    assert result_exit_code(result) == 1
    assert result_exit_code(
        result, report_only=True, reconciliation=True
    ) == 0
    try:
        result_exit_code(result, report_only=True)
    except ValueError as exc:
        assert str(exc) == "report-only mode requires programme reconciliation"
    else:
        raise AssertionError("report-only mode must fail closed outside reconciliation")
    assert result_exit_code({"valid": True}) == 0


class FakeProgrammeClient(FakePostClient):
    def __init__(self, visible: list[str], feed: list[str] | None = None) -> None:
        super().__init__(visible)
        self.feed = feed or visible

    def fetch_author_feed(self, actor: str, *, limit: int = 100):
        return [{"post": {"uri": uri}} for uri in self.feed[:limit]]
