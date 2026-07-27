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
    assert result["duplicates"][0]["keeper_uri"].endswith("/two")
    assert result["duplicates"][0]["duplicate_uris"] == ["at://did:plc:acc/app.bsky.feed.post/one"]


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
    assert result["resolved_cleanup_deletions"] == []
    assert result["unexpected_missing"] == result["deleted_or_missing"]
    assert result["missing_audit"][0]["uri"].endswith("/untracked")


def test_cleanup_receipt_resolves_only_confirmed_missing_records(tmp_path) -> None:
    registry = tmp_path / "registry.json"
    registry.write_text(
        json.dumps(
            {
                "mirrors": [
                    {
                        "mirror_id": "agency",
                        "handle": "agency.bsky.social",
                        "source_ids": ["allowed"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    keeper = "at://did:plc:a/app.bsky.feed.post/keeper"
    deleted = "at://did:plc:a/app.bsky.feed.post/deleted"
    audit = tmp_path / "audit.jsonl"
    audit.write_text(
        "\n".join(
            json.dumps(row)
            for row in (
                {
                    "mirror_id": "agency",
                    "record_id": "r1",
                    "rendered_hash": "same",
                    "source_id": "allowed",
                    "uri": keeper,
                    "status": "posted",
                },
                {
                    "mirror_id": "agency",
                    "record_id": "r1",
                    "rendered_hash": "same",
                    "source_id": "retired",
                    "uri": deleted,
                    "status": "posted",
                },
            )
        )
        + "\n",
        encoding="utf-8",
    )
    receipt = tmp_path / "cleanup-apply.json"
    receipt.write_text(
        json.dumps(
            {
                "mirror_id": "agency",
                "apply_requested": True,
                "status": "apply_completed",
                "credential_material_recorded": False,
                "delete_requests_succeeded": [deleted],
                "already_missing": [],
            }
        ),
        encoding="utf-8",
    )

    result = reconcile_programme_audit(
        registry_path=registry,
        mirror_id="agency",
        audit_paths=[audit],
        client=FakeProgrammeClient(visible=[keeper], feed=[keeper]),
        cleanup_apply_path=receipt,
    )

    assert result["duplicates"] == []
    assert result["excluded_sources"] == []
    assert result["resolved_cleanup_deletions"] == [
        {"uri": deleted, "reason": "confirmed_cleanup_receipt"}
    ]
    assert result["unexpected_missing"] == []
    assert result["cleanup_approval_packet"]["candidates"] == []
    assert result["cleanup_approval_packet"]["requires_exact_uri_approval"] is False
    assert result["valid"] is True


def test_dry_run_receipt_does_not_resolve_missing_record(tmp_path) -> None:
    receipt = tmp_path / "cleanup-apply.json"
    receipt.write_text(
        json.dumps(
            {
                "mirror_id": "agency",
                "apply_requested": False,
                "status": "dry_run",
                "credential_material_recorded": False,
                "already_missing": ["at://did:plc:a/app.bsky.feed.post/missing"],
            }
        ),
        encoding="utf-8",
    )

    from scripts.verify_archive_mirror_posts import _confirmed_cleanup_uris

    assert _confirmed_cleanup_uris(receipt, "agency") == set()


def test_cleanup_prefers_reconciled_post_as_duplicate_keeper(tmp_path) -> None:
    registry = tmp_path / "registry.json"
    registry.write_text(
        json.dumps(
            {
                "mirrors": [
                    {
                        "mirror_id": "agency",
                        "handle": "agency.bsky.social",
                        "source_ids": ["agency-x-feed"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    failed_uri = "at://did:plc:a/app.bsky.feed.post/z-failed"
    posted_uri = "at://did:plc:a/app.bsky.feed.post/a-posted"
    audit = tmp_path / "audit.jsonl"
    audit.write_text(
        "\n".join(
            json.dumps(row)
            for row in [
                {
                    "mirror_id": "agency",
                    "record_id": "x:123",
                    "rendered_hash": "same",
                    "source_id": "agency-x-feed",
                    "uri": failed_uri,
                    "reconciled": False,
                    "status": "reconcile_failed",
                    "attempted_at": "2026-07-22T00:00:00Z",
                },
                {
                    "mirror_id": "agency",
                    "record_id": "x:123",
                    "rendered_hash": "same",
                    "source_id": "agency-x-feed",
                    "uri": posted_uri,
                    "reconciled": True,
                    "status": "posted",
                    "attempted_at": "2026-07-22T00:01:00Z",
                },
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = reconcile_programme_audit(
        registry_path=registry,
        mirror_id="agency",
        audit_paths=[audit],
        client=FakeProgrammeClient(visible=[failed_uri, posted_uri]),
    )

    assert result["duplicates"] == [
        {
            "record_id": "x:123",
            "rendered_hash": "same",
            "keeper_uri": posted_uri,
            "duplicate_uris": [failed_uri],
            "uris": sorted([failed_uri, posted_uri]),
        }
    ]
    assert result["cleanup_approval_packet"]["candidates"] == [
        {
            "uri": failed_uri,
            "reasons": ["duplicate"],
            "requires_exact_uri_approval": True,
            "action": "review_for_deletion",
        }
    ]


def test_cleanup_infers_unique_legacy_source_id_from_record_platform(tmp_path) -> None:
    registry = tmp_path / "registry.json"
    registry.write_text(
        json.dumps(
            {
                "mirrors": [
                    {
                        "mirror_id": "agency",
                        "handle": "agency.bsky.social",
                        "source_ids": ["agency-linkedin-feed"],
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
                "record_id": "linkedin_public_snapshot:123",
                "rendered_hash": "hash",
                "source_id": "",
                "uri": "at://did:plc:a/app.bsky.feed.post/tracked",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    result = reconcile_programme_audit(
        registry_path=registry,
        mirror_id="agency",
        audit_paths=[audit],
        client=FakeProgrammeClient(visible=["at://did:plc:a/app.bsky.feed.post/tracked"]),
    )

    assert result["excluded_sources"] == []


def test_cleanup_ignores_only_proven_pre_activation_feed_posts(tmp_path) -> None:
    registry = tmp_path / "registry.json"
    registry.write_text(
        json.dumps(
            {
                "mirrors": [
                    {
                        "mirror_id": "agency",
                        "handle": "agency.bsky.social",
                        "source_ids": [],
                        "activated_at": "2026-07-22T08:00:00+00:00",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    client = FakeProgrammeClient(
        visible=[],
        feed=[
            {
                "post": {
                    "uri": "at://did:plc:a/app.bsky.feed.post/legacy",
                    "record": {"createdAt": "2026-07-22T07:59:59Z"},
                }
            },
            {
                "post": {
                    "uri": "at://did:plc:a/app.bsky.feed.post/current",
                    "record": {"createdAt": "2026-07-22T08:00:00Z"},
                }
            },
        ],
    )

    result = reconcile_programme_audit(
        registry_path=registry,
        mirror_id="agency",
        audit_paths=[],
        client=client,
    )

    assert result["pre_activation_posts_ignored"] == ["at://did:plc:a/app.bsky.feed.post/legacy"]
    assert result["missing_audit"] == [
        {
            "uri": "at://did:plc:a/app.bsky.feed.post/current",
            "reason": "public_post_missing_audit",
        }
    ]


def test_reconciliation_findings_remain_strict_unless_report_only() -> None:
    result = {"valid": False}

    assert result_exit_code(result) == 1
    assert result_exit_code(result, report_only=True, reconciliation=True) == 0
    try:
        result_exit_code(result, report_only=True)
    except ValueError as exc:
        assert str(exc) == "report-only mode requires programme reconciliation"
    else:
        raise AssertionError("report-only mode must fail closed outside reconciliation")
    assert result_exit_code({"valid": True}) == 0


class FakeProgrammeClient(FakePostClient):
    def __init__(
        self,
        visible: list[str],
        feed: list[str | dict] | None = None,
    ) -> None:
        super().__init__(visible)
        self.feed = feed or visible

    def fetch_author_feed(self, actor: str, *, limit: int = 100):
        return [
            item if isinstance(item, dict) else {"post": {"uri": item}}
            for item in self.feed[:limit]
        ]
