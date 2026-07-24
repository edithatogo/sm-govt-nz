import json
from pathlib import Path

import pytest

from src.bluesky_mirror_programme import (
    MirrorRecord,
    build_registry_from_manifest,
    handle_candidates,
    load_archive_records,
    render_thread,
    publish_next,
    preflight_account,
    render_record,
    validate_registry,
    workflow_matrix,
)


def registry_row(**overrides):
    row = {
        "mirror_id": "agency",
        "agency_id": "agency",
        "agency_name": "Agency",
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
        app_password="app-password",
        login=lambda handle, password: logged_in.append((handle, password)),
        fetch_profile=lambda _handle: {
            "did": "did:plc:agency",
            "displayName": "Agency Archive Mirror",
            "description": "Unofficial automated archive mirror.",
            "labels": [{"val": "bot"}],
        },
    )

    assert result["valid"] is True
    assert logged_in == [("agency-archive.bsky.social", "app-password")]


def test_preflight_rejects_ambiguous_profile() -> None:
    with pytest.raises(RuntimeError, match="archive disclosure"):
        preflight_account(
            registry(registry_row()),
            "agency",
            handle="agency-archive.bsky.social",
            app_password="app-password",
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
    record = MirrorRecord("linkedin-2", "agency", "linkedin-source", "linkedin", "2026-07-22", "word " * 500, "https://www.linkedin.com/posts/example-2")
    parts = render_thread(record, historical=True)
    assert 1 < len(parts) <= 4
    assert parts[0].startswith("[Archived 2026-07-22] [linkedin] [1/")
    assert all(len(part) <= 300 for part in parts)
    assert parts[-1].endswith("https://www.linkedin.com/posts/example-2")


def test_publish_dry_run_never_calls_sender(tmp_path: Path) -> None:
    archive = tmp_path / "historical_archive_normalized" / "x"
    archive.mkdir(parents=True)
    (archive / "2026-07.jsonl").write_text(
        json.dumps({"record_id": "r1", "agency_id": "agency", "source_id": "source-1", "source_platform": "x", "content": "Public update", "original_created_at": "2020-01-02T00:00:00Z", "source_url": "https://x.com/a/status/1", "visibility": "public"}) + "\n",
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


def test_live_sender_receives_one_already_attributed_rendering(
    tmp_path: Path, monkeypatch
) -> None:
    archive = tmp_path / "historical_archive_normalized" / "x"
    archive.mkdir(parents=True)
    (archive / "2026-07.jsonl").write_text(
        json.dumps({"record_id": "r1", "agency_id": "agency", "source_id": "source-1", "source_platform": "x", "content": "Public update", "original_created_at": "2020-01-02T00:00:00Z", "source_url": "https://x.com/a/status/1", "visibility": "public"}) + "\n",
        encoding="utf-8",
    )
    sent = []
    monkeypatch.setenv("BLUESKY_MIRRORING_ENABLED", "true")
    monkeypatch.setenv("BLUESKY_HANDLE", "agency-archive.bsky.social")
    monkeypatch.setenv("BLUESKY_APP_PASSWORD", "app-password")

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


def test_archive_workflows_do_not_receive_posting_credentials() -> None:
    root = Path(".github/workflows")
    for workflow in root.glob("archive*.yml"):
        text = workflow.read_text(encoding="utf-8")
        assert "BLUESKY_APP_PASSWORD" not in text
        assert "manage_bluesky_mirror_programme.py publish" not in text


def test_source_allowlist_excludes_retired_sibling_records(tmp_path: Path) -> None:
    shard = tmp_path / "x" / "2026-07.jsonl"
    shard.parent.mkdir(parents=True)
    rows = [
        {"agency_id": "agency", "source_id": "current", "record_id": "r1", "content": "current", "source_url": "https://x.example/current", "original_created_at": "2026-07-01"},
        {"agency_id": "agency", "source_id": "retired", "record_id": "r2", "content": "retired", "source_url": "https://x.example/retired", "original_created_at": "2017-01-01"},
    ]
    shard.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    records = load_archive_records({"agency_id": "agency", "source_ids": ["current"]}, tmp_path)
    assert [record.record_id for record in records] == ["r1"]
