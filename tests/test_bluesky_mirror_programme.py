import json
from pathlib import Path

import pytest

from src.bluesky_mirror_programme import (
    MirrorRecord,
    canonicalize_source_url,
    credential_health_report,
    build_registry_from_manifest,
    evaluate_source_eligibility,
    handle_candidates,
    load_archive_records,
    load_runtime_state,
    migrate_runtime_state,
    render_thread,
    publish_next,
    preflight_account,
    recover_account,
    render_record,
    validate_registry,
    workflow_matrix,
)


def registry_row(**overrides):
    row = {
        "mirror_id": "agency",
        "agency_id": "agency",
        "agency_name": "Agency",
        "public_name": "Agency",
        "handle": "agency-archive.bsky.social",
        "environment": "bluesky-mirror-agency",
        "registration_alias_slug": "agency",
        "lifecycle_state": "backfilling",
        "enabled": True,
        "backfill_state": "active",
        "health_state": "healthy",
        "source_ids": ["source-1"],
        "source_urls": [],
        "source_platforms": ["x"],
        "issue_number": None,
        "evidence": [],
        "activated_at": "2026-07-01T00:00:00Z",
    }
    row.update(overrides)
    return row


def registry(*rows):
    return {"schema_version": 2, "mirrors": list(rows)}


def test_registry_forbids_secrets_and_complete_email_aliases() -> None:
    validate_registry(registry(registry_row()))
    with pytest.raises(ValueError, match="Secret-like"):
        validate_registry(registry(registry_row(app_password="secret")))
    with pytest.raises(ValueError, match="registration aliases"):
        validate_registry(registry(registry_row(note="edithatogo+bluesky-agency@gmail.com")))


def test_registry_builder_groups_sources_by_agency() -> None:
    manifest = {
        "sources": [
            {"agency_id": "Agency One", "agency_name": "Agency One", "platform": "x", "source_id": "x-1", "url": "https://x.com/one"},
            {"agency_id": "Agency One", "agency_name": "Agency One", "platform": "bluesky", "source_id": "b-1", "url": "https://bsky.app/profile/one"},
            {"agency_id": "Agency One", "agency_name": "Agency One", "platform": "rss", "source_id": "rss-1", "url": "https://example/rss"},
        ]
    }
    result = build_registry_from_manifest(manifest, {"schema_version": 2, "mirrors": []})
    agency = next(row for row in result["mirrors"] if row["mirror_id"] == "agency-one")
    index = next(
        row for row in result["mirrors"] if row["mirror_id"] == "nzgov-social-archive-index"
    )
    assert agency["source_ids"] == ["b-1", "x-1"]
    assert index["account_role"] == "corpus_index"


def test_registry_builder_preserves_public_name_and_acc_handle_policy() -> None:
    manifest = {
        "sources": [
            {
                "agency_id": "Accident Compensation Corporation",
                "agency_name": "Accident Compensation Corporation",
                "platform": "linkedin",
                "source_id": "acc-linkedin",
                "url": "https://www.linkedin.com/company/acc-new-zealand",
            }
        ]
    }
    existing = registry(
        registry_row(
            mirror_id="accident-compensation-corporation",
            agency_id="accident-compensation-corporation",
            agency_name="Accident Compensation Corporation",
            public_name="ACC",
            organisation_abbreviation="acc",
            jurisdiction="nz",
            handle_policy_version=1,
            handle="acc-nz-arc.bsky.social",
        )
    )
    result = build_registry_from_manifest(manifest, existing)
    acc = next(
        row
        for row in result["mirrors"]
        if row["mirror_id"] == "accident-compensation-corporation"
    )
    assert acc["public_name"] == "ACC"
    assert acc["handle"] == "acc-nz-arc.bsky.social"
    assert acc["handle_candidates"] == [
        "acc-nz-arc.bsky.social",
        "acc-nz-arc-2.bsky.social",
    ]


def test_handle_policy_and_matrix_are_deterministic() -> None:
    assert handle_candidates("Agency One") == [
        "agency-one-nz-arc.bsky.social",
        "agency-one-nz-arc-2.bsky.social",
    ]
    assert handle_candidates("Accident Compensation Corporation", abbreviation="ACC") == [
        "acc-nz-arc.bsky.social",
        "acc-nz-arc-2.bsky.social",
    ]
    assert workflow_matrix(registry(registry_row()), mode="backfill")["include"][0]["mirror_id"] == "agency"
    assert workflow_matrix(
        registry(registry_row()),
        mode="backfill",
        runtime_state={"accounts": {"agency": {"backfill_complete": True}}},
    ) == {"include": []}


def test_workflow_matrix_manual_selector_is_account_isolated() -> None:
    selected = workflow_matrix(
        registry(
            registry_row(mirror_id="acc", agency_id="acc"),
            registry_row(mirror_id="courts", agency_id="courts"),
        ),
        mode="backfill",
        mirror_id="acc",
    )

    assert [row["mirror_id"] for row in selected["include"]] == ["acc"]


def test_jurisdictional_handle_policy_requires_abbreviation_jurisdiction_and_did() -> None:
    acc = registry_row(
        handle="acc-nz-arc.bsky.social",
        handle_policy_version=1,
        organisation_abbreviation="acc",
        jurisdiction="nz",
        account_did="did:plc:vxltrdhni2dfsm4actryhj4n",
    )
    validate_registry(registry(acc))
    with pytest.raises(ValueError, match="jurisdictional handle policy"):
        validate_registry(registry({**acc, "handle": "accident-comp-archive.bsky.social"}))
    with pytest.raises(ValueError, match="invalid AT Protocol DID"):
        validate_registry(registry({**acc, "account_did": "not-a-did"}))


def test_preflight_requires_archive_disclosure_and_bot_label() -> None:
    logged_in = []

    result = preflight_account(
        registry(registry_row()),
        "agency",
        handle="agency-archive.bsky.social",
        app_password="abcd-efgh-ijkl-mnop",
        login=lambda handle, password: logged_in.append((handle, password)),
        fetch_profile=lambda _handle: {
            "did": "did:plc:agency",
            "displayName": "Agency Archive Mirror",
            "description": "Unofficial automated archive mirror.",
            "labels": [{"val": "bot"}],
        },
    )

    assert result["valid"] is True
    assert logged_in == [("agency-archive.bsky.social", "abcd-efgh-ijkl-mnop")]


def test_preflight_rejects_ambiguous_profile() -> None:
    with pytest.raises(RuntimeError, match="archive disclosure"):
        preflight_account(
            registry(registry_row()),
            "agency",
            handle="agency-archive.bsky.social",
            app_password="abcd-efgh-ijkl-mnop",
            login=lambda _handle, _password: None,
            fetch_profile=lambda _handle: {"displayName": "Agency", "description": "Official updates", "labels": []},
        )


def test_rendered_history_is_bounded_and_attributed() -> None:
    record = MirrorRecord("r1", "agency", "source-1", "x", "2020-01-02T00:00:00Z", "A" * 500, "https://x.com/a/status/1")
    text = render_record(record, historical=True)
    assert len(text) <= 300
    assert text.startswith("[Archived 2020-01-02]")
    assert "Original: https://x.com/a/status/1" in text


def test_long_linkedin_posts_are_faithful_bounded_excerpts() -> None:
    record = MirrorRecord(
        "linkedin-1",
        "agency",
        "linkedin-source",
        "linkedin",
        "2026-07-22T00:00:00Z",
        "Long LinkedIn post " * 100,
        "https://www.linkedin.com/posts/example-1",
    )
    text = render_record(record, historical=True)
    assert len(text) <= 300
    assert text.startswith("[Archived 2026-07-22] [linkedin]")
    assert "Original: https://www.linkedin.com/posts/example-1" in text


def test_long_linkedin_posts_can_be_planned_as_bounded_numbered_thread() -> None:
    record = MirrorRecord(
        "linkedin-2",
        "agency",
        "linkedin-source",
        "linkedin",
        "2026-07-22",
        "word " * 500,
        "https://www.linkedin.com/posts/example-2",
        public_name="ACC",
    )
    parts = render_thread(record, historical=True)
    assert 1 < len(parts) <= 4
    assert parts[0].startswith("[Archived 2026-07-22] [ACC] [linkedin] [1/")
    assert all(len(part) <= 300 for part in parts)
    assert "…\n\nOriginal:" in parts[-1]
    assert parts[-1].endswith("https://www.linkedin.com/posts/example-2")
    assert parts == render_thread(record, historical=True)


def test_long_unbroken_content_falls_back_to_a_bounded_excerpt() -> None:
    record = MirrorRecord(
        "linkedin-3",
        "agency",
        "linkedin-source",
        "linkedin",
        "2026-07-22",
        "A" * 1000,
        "https://www.linkedin.com/posts/example-3",
        public_name="ACC",
    )
    parts = render_thread(record, historical=True)
    assert len(parts) == 1
    assert len(parts[0]) <= 300
    assert parts[0].endswith("https://www.linkedin.com/posts/example-3")


def test_publish_dry_run_never_calls_sender(tmp_path: Path) -> None:
    archive = tmp_path / "historical_archive_normalized" / "x"
    archive.mkdir(parents=True)
    (archive / "2026-07.jsonl").write_text(
        json.dumps({"record_id": "r1", "agency_id": "agency", "source_id": "source-1", "source_platform": "x", "source_kind": "post", "content": "Public update", "original_created_at": "2020-01-02T00:00:00Z", "source_url": "https://x.com/a/status/1", "visibility": "public"}) + "\n",
        encoding="utf-8",
    )
    called = False

    def sender(_post):
        nonlocal called
        called = True
        raise AssertionError("dry-run posted")

    result = publish_next(registry(registry_row()), "agency", mode="backfill", dry_run=True, archive_root=archive, state_path=tmp_path / "state.json", audit_path=tmp_path / "audit.jsonl", sender=sender)
    assert result["status"] == "dry_run"
    assert called is False


def test_paused_account_dry_run_writes_eligibility_without_sending(
    tmp_path: Path,
) -> None:
    archive = tmp_path / "historical_archive_normalized" / "x"
    archive.mkdir(parents=True)
    (archive / "2026-07.jsonl").write_text(
        json.dumps(
            {
                "record_id": "r1",
                "agency_id": "agency",
                "source_id": "source-1",
                    "source_platform": "x",
                    "source_kind": "post",
                "content": "Public update",
                "original_created_at": "2020-01-02T00:00:00Z",
                "source_url": "https://x.com/a/status/1",
                "visibility": "public",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    state_path = tmp_path / "state.json"
    state_path.write_text(
        json.dumps({"accounts": {"agency": {"paused": True}}}),
        encoding="utf-8",
    )
    report_path = tmp_path / "eligibility.json"
    called = False

    def sender(_post):
        nonlocal called
        called = True
        raise AssertionError("paused dry-run posted")

    result = publish_next(
        registry(
            registry_row(
                source_urls=["https://x.com/a"],
            )
        ),
        "agency",
        mode="backfill",
        dry_run=True,
        archive_root=archive,
        state_path=state_path,
        audit_path=tmp_path / "audit.jsonl",
        eligibility_report_path=report_path,
        sender=sender,
    )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert result["status"] == "dry_run"
    assert result["posted"] == 0
    assert report["accepted"] == 1
    assert called is False


def test_live_sender_receives_one_already_attributed_rendering(
    tmp_path: Path, monkeypatch
) -> None:
    archive = tmp_path / "historical_archive_normalized" / "x"
    archive.mkdir(parents=True)
    (archive / "2026-07.jsonl").write_text(
            json.dumps({"record_id": "r1", "agency_id": "agency", "source_id": "source-1", "source_platform": "x", "source_kind": "post", "content": "Public update", "original_created_at": "2020-01-02T00:00:00Z", "source_url": "https://x.com/a/status/1", "visibility": "public"}) + "\n",
        encoding="utf-8",
    )
    sent = []
    monkeypatch.setenv("BLUESKY_MIRRORING_ENABLED", "true")
    monkeypatch.setenv("BLUESKY_HANDLE", "agency-archive.bsky.social")
    monkeypatch.setenv("BLUESKY_APP_PASSWORD", "abcd-efgh-ijkl-mnop")

    result = publish_next(
        registry(registry_row()),
        "agency",
        mode="backfill",
        archive_root=archive,
        state_path=tmp_path / "state.json",
        audit_path=tmp_path / "audit.jsonl",
        dead_letter_path=tmp_path / "dead.jsonl",
        sender=lambda post: sent.append(post) or __import__("src.syndication", fromlist=["SyndicationResult"]).SyndicationResult("bluesky", True, detail="at://did:plc:a/app.bsky.feed.post/1"),
        readback=lambda _uri: True,
    )

    assert result["posted"] == 1
    assert sent[0]["text"].count("Original:") == 1


def test_delayed_readback_resumes_without_duplicate_submission(
    tmp_path: Path, monkeypatch
) -> None:
    archive = tmp_path / "historical_archive_normalized" / "x"
    archive.mkdir(parents=True)
    (archive / "2026-07.jsonl").write_text(
        json.dumps(
            {
                "record_id": "r1",
                "agency_id": "agency",
                "source_id": "source-1",
                "source_platform": "x",
                "source_kind": "post",
                "content": "Public update",
                "original_created_at": "2020-01-02T00:00:00Z",
                "source_url": "https://x.com/a/status/1",
                "visibility": "public",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("BLUESKY_MIRRORING_ENABLED", "true")
    monkeypatch.setenv("BLUESKY_HANDLE", "agency-archive.bsky.social")
    monkeypatch.setenv("BLUESKY_APP_PASSWORD", "abcd-efgh-ijkl-mnop")
    state_path = tmp_path / "state.json"
    sent = []
    visible = iter((False, True))

    first = publish_next(
        registry(registry_row()),
        "agency",
        mode="backfill",
        archive_root=archive,
        state_path=state_path,
        audit_path=tmp_path / "audit.jsonl",
        sender=lambda post: sent.append(post)
        or __import__("src.syndication", fromlist=["SyndicationResult"]).SyndicationResult(
            "bluesky", True, detail="at://did:plc:a/app.bsky.feed.post/1"
        ),
        readback=lambda _uri: next(visible),
    )
    second = publish_next(
        registry(registry_row()),
        "agency",
        mode="backfill",
        archive_root=archive,
        state_path=state_path,
        audit_path=tmp_path / "audit.jsonl",
        sender=lambda _post: (_ for _ in ()).throw(
            AssertionError("reserved publication was submitted twice")
        ),
        readback=lambda _uri: next(visible),
    )

    assert first["status"] == "pending_reconciliation"
    assert second["status"] == "posted"
    assert len(sent) == 1
    state = json.loads(state_path.read_text(encoding="utf-8"))
    publication = next(iter(state["accounts"]["agency"]["publications"].values()))
    assert publication["state"] == "reconciled"
    audit_rows = [
        json.loads(line)
        for line in (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert audit_rows[-1]["status"] == "posted"
    assert audit_rows[-1]["publication_state"] == "reconciled"


def test_ambiguous_submission_failure_is_reserved_and_not_retried(
    tmp_path: Path, monkeypatch
) -> None:
    archive = tmp_path / "historical_archive_normalized" / "x"
    archive.mkdir(parents=True)
    (archive / "2026-07.jsonl").write_text(
        json.dumps(
            {
                "record_id": "r1",
                "agency_id": "agency",
                "source_id": "source-1",
                "source_platform": "x",
                "source_kind": "post",
                "content": "Public update",
                "original_created_at": "2020-01-02T00:00:00Z",
                "source_url": "https://x.com/a/status/1",
                "visibility": "public",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("BLUESKY_MIRRORING_ENABLED", "true")
    monkeypatch.setenv("BLUESKY_HANDLE", "agency-archive.bsky.social")
    monkeypatch.setenv("BLUESKY_APP_PASSWORD", "abcd-efgh-ijkl-mnop")
    state_path = tmp_path / "state.json"
    calls = 0

    def ambiguous_sender(_post):
        nonlocal calls
        calls += 1
        raise TimeoutError("response lost after submission")

    first = publish_next(
        registry(registry_row()),
        "agency",
        mode="backfill",
        archive_root=archive,
        state_path=state_path,
        audit_path=tmp_path / "audit.jsonl",
        sender=ambiguous_sender,
        readback=lambda _uri: False,
    )
    second = publish_next(
        registry(registry_row()),
        "agency",
        mode="backfill",
        archive_root=archive,
        state_path=state_path,
        audit_path=tmp_path / "audit.jsonl",
        sender=ambiguous_sender,
        readback=lambda _uri: False,
    )

    assert first["status"] == "pending_reconciliation"
    assert second["status"] == "pending_reconciliation"
    assert calls == 1
    assert json.loads(state_path.read_text(encoding="utf-8"))["accounts"]["agency"].get(
        "paused"
    ) is not True


def test_monolithic_runtime_state_migrates_without_overwriting_partitions(
    tmp_path: Path,
) -> None:
    legacy = tmp_path / "state.json"
    state_dir = tmp_path / "state"
    legacy.write_text(
        json.dumps(
            {
                "accounts": {
                    "agency-a": {"paused": True},
                    "agency-b": {"backfill_complete": True},
                }
            }
        ),
        encoding="utf-8",
    )
    state_dir.mkdir()
    (state_dir / "agency-a.json").write_text(
        json.dumps({"accounts": {"agency-a": {"paused": False}}}),
        encoding="utf-8",
    )

    result = migrate_runtime_state(legacy, state_dir)
    aggregate = load_runtime_state(legacy, state_dir)

    assert result["preserved"] == ["agency-a"]
    assert result["migrated"] == ["agency-b"]
    assert aggregate["accounts"]["agency-a"]["paused"] is False
    assert aggregate["accounts"]["agency-b"]["backfill_complete"] is True


def test_partitioned_runtime_updates_preserve_unrelated_accounts(tmp_path: Path) -> None:
    state_dir = tmp_path / "state"
    migrate_runtime_state(
        tmp_path / "missing-legacy.json",
        state_dir,
    )
    for mirror_id, value in (("agency-a", True), ("agency-b", False)):
        path = state_dir / f"{mirror_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"accounts": {mirror_id: {"paused": value}}}),
            encoding="utf-8",
        )

    agency_a = json.loads((state_dir / "agency-a.json").read_text(encoding="utf-8"))
    agency_a["accounts"]["agency-a"]["paused"] = False
    (state_dir / "agency-a.json").write_text(json.dumps(agency_a), encoding="utf-8")
    aggregate = load_runtime_state(tmp_path / "missing-legacy.json", state_dir)

    assert aggregate["accounts"]["agency-a"]["paused"] is False
    assert aggregate["accounts"]["agency-b"]["paused"] is False


def test_recovery_resumes_only_after_all_publications_reconcile(tmp_path: Path) -> None:
    state_path = tmp_path / "agency.json"
    state_path.write_text(
        json.dumps(
            {
                "accounts": {
                    "agency": {
                        "paused": True,
                        "pause_reason": "publication reconciliation exhausted",
                        "publications": {
                            "key": {
                                "state": "pending_reconciliation",
                                "record_id": "r1",
                                "uri": "at://did:plc:a/app.bsky.feed.post/1",
                            }
                        },
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    report_path = tmp_path / "recovery.json"

    diagnosis = recover_account(
        registry(registry_row()),
        "agency",
        state_path=state_path,
        report_path=report_path,
        probe=lambda _uri: "reconciled",
    )
    applied = recover_account(
        registry(registry_row()),
        "agency",
        apply=True,
        state_path=state_path,
        report_path=report_path,
        probe=lambda _uri: "reconciled",
    )

    assert diagnosis["status"] == "ready_to_resume"
    assert diagnosis["resumed"] is False
    assert applied["status"] == "resumed"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["accounts"]["agency"]["paused"] is False
    assert (
        state["accounts"]["agency"]["publications"]["key"]["state"] == "reconciled"
    )


@pytest.mark.parametrize(
    ("pause_reason", "publication", "classification"),
    [
        (
            "publication reconciliation exhausted",
            {"state": "pending_reconciliation", "record_id": "r1", "uri": ""},
            "ambiguous_missing_uri",
        ),
        (
            "publication reconciliation exhausted",
            {
                "state": "pending_reconciliation",
                "record_id": "r1",
                "uri": "at://did:plc:a/app.bsky.feed.post/1",
            },
            "deleted",
        ),
        (
            "authentication failed",
            {
                "state": "pending_reconciliation",
                "record_id": "r1",
                "uri": "at://did:plc:a/app.bsky.feed.post/1",
            },
            "reconciled",
        ),
    ],
)
def test_recovery_keeps_ambiguous_deleted_and_nonrecoverable_pauses(
    tmp_path: Path,
    pause_reason: str,
    publication: dict,
    classification: str,
) -> None:
    state_path = tmp_path / "agency.json"
    state_path.write_text(
        json.dumps(
            {
                "accounts": {
                    "agency": {
                        "paused": True,
                        "pause_reason": pause_reason,
                        "publications": {"key": publication},
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    result = recover_account(
        registry(registry_row()),
        "agency",
        apply=True,
        state_path=state_path,
        report_path=tmp_path / "recovery.json",
        probe=lambda _uri: classification,
    )

    assert result["status"] == "recovery_blocked"
    assert result["resumed"] is False
    assert json.loads(state_path.read_text(encoding="utf-8"))["accounts"]["agency"][
        "paused"
    ] is True


def test_preflight_rejects_primary_password_shape() -> None:
    with pytest.raises(RuntimeError, match="primary passwords are forbidden"):
        preflight_account(
            registry(registry_row()),
            "agency",
            handle="agency-archive.bsky.social",
            app_password="Auckland01!!!",
            login=lambda _handle, _password: None,
        )


def test_credential_health_report_never_exposes_secret_value() -> None:
    secret = "abcd-efgh-ijkl-mnop"
    result = credential_health_report(
        registry(registry_row()),
        "agency",
        handle="agency-archive.bsky.social",
        app_password=secret,
    )

    assert result["valid"] is True
    assert result["credential_mode"] == "app_password"
    assert secret not in json.dumps(result)


def test_archive_workflows_do_not_receive_posting_credentials() -> None:
    root = Path(".github/workflows")
    for workflow in root.glob("archive*.yml"):
        text = workflow.read_text(encoding="utf-8")
        assert "BLUESKY_APP_PASSWORD" not in text
        assert "manage_bluesky_mirror_programme.py publish" not in text


def test_manual_mirror_workflows_default_to_non_posting_dry_run() -> None:
    for name in (
        "bluesky_mirror_ongoing.yml",
        "bluesky_mirror_historical_backfill.yml",
    ):
        text = (Path(".github/workflows") / name).read_text(encoding="utf-8")
        assert "dry_run:" in text
        assert "default: true" in text
        assert 'args+=(--dry-run)' in text
        assert (
            "github.event_name == 'workflow_dispatch' && inputs.dry_run == true"
            in text
        )
        assert (
            "inputs.dry_run == true && 'false' || vars.BLUESKY_MIRRORING_ENABLED"
            in text
        )


def test_source_allowlist_excludes_retired_sibling_records(tmp_path: Path) -> None:
    shard = tmp_path / "x" / "2026-07.jsonl"
    shard.parent.mkdir(parents=True)
    rows = [
        {"agency_id": "agency", "source_id": "current", "source_platform": "x", "source_kind": "post", "visibility": "public", "record_id": "r1", "content": "current", "source_url": "https://x.example/current", "original_created_at": "2026-07-01"},
        {"agency_id": "agency", "source_id": "retired", "source_platform": "x", "source_kind": "post", "visibility": "public", "record_id": "r2", "content": "retired", "source_url": "https://x.example/retired", "original_created_at": "2017-01-01"},
    ]
    shard.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    records = load_archive_records(
        {
            "mirror_id": "agency",
            "agency_id": "agency",
            "source_ids": ["current"],
            "source_platforms": ["x"],
            "source_urls": ["https://x.example/current"],
        },
        tmp_path,
    )
    assert [record.record_id for record in records] == ["r1"]


def test_source_eligibility_fails_closed_and_normalizes_urls() -> None:
    account = registry_row(
        source_ids=["linkedin-current"],
        source_platforms=["linkedin"],
        source_urls=["https://www.linkedin.com/company/agency/?trk=public"],
        excluded_source_urls=["https://linkedin.com/posts/retired/?tracking=1"],
    )
    valid = {
        "record_id": "valid",
        "agency_id": "agency",
        "source_id": "linkedin-current",
        "source_platform": "linkedin",
        "source_kind": "social_feed",
        "visibility": "public",
        "source_url": "https://www.linkedin.com/posts/current/?tracking=1",
    }
    assert evaluate_source_eligibility(account, valid).eligible is True
    assert canonicalize_source_url("http://WWW.TWITTER.COM/a/?x=1") == "https://x.com/a"

    fixtures = [
        ({**valid, "source_id": ""}, "missing_source_id"),
        ({**valid, "source_platform": "x"}, "source_platform_not_allowed"),
        ({**valid, "agency_id": "sibling"}, "agency_mismatch"),
        ({**valid, "source_kind": "public_profile_snapshot"}, "source_kind_not_mirrorable"),
        ({key: value for key, value in valid.items() if key != "source_kind"}, "missing_source_kind"),
        (
            {
                **valid,
                "source_url": "http://www.linkedin.com/posts/retired#fragment",
            },
            "source_url_excluded",
        ),
        ({key: value for key, value in valid.items() if key != "visibility"}, "missing_visibility"),
    ]
    for raw, reason in fixtures:
        decision = evaluate_source_eligibility(account, raw)
        assert decision.eligible is False
        assert decision.reason == reason


def test_eligibility_report_records_bounded_rejection_reasons(tmp_path: Path) -> None:
    shard = tmp_path / "linkedin" / "2026-07.jsonl"
    shard.parent.mkdir(parents=True)
    rows = [
        {
            "record_id": "valid",
            "agency_id": "agency",
            "source_id": "linkedin-current",
            "source_platform": "linkedin",
            "source_kind": "social_feed",
            "visibility": "public",
            "content": "Public update",
            "source_url": "https://linkedin.com/posts/current",
        },
        {
            "record_id": "legacy",
            "agency_id": "agency",
            "source_platform": "linkedin",
            "visibility": "public",
            "content": "Legacy update",
            "source_url": "https://linkedin.com/posts/legacy",
        },
    ]
    shard.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8"
    )
    report_path = tmp_path / "eligibility.json"
    records = load_archive_records(
        {
            "mirror_id": "agency",
            "agency_id": "agency",
            "source_ids": ["linkedin-current"],
            "source_platforms": ["linkedin"],
            "source_urls": ["https://linkedin.com/company/agency"],
        },
        tmp_path,
        eligibility_report_path=report_path,
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert [record.record_id for record in records] == ["valid"]
    assert report["accepted"] == 1
    assert report["rejected"] == 1
    assert report["rejection_reason_counts"] == {"missing_source_id": 1}
