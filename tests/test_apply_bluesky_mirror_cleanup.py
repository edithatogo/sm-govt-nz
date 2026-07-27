import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import apply_bluesky_mirror_cleanup as cleanup
from scripts.apply_bluesky_mirror_cleanup import apply_cleanup


DID = "did:plc:agency"
URI_ONE = f"at://{DID}/app.bsky.feed.post/one"
URI_TWO = f"at://{DID}/app.bsky.feed.post/two"


def write_inputs(tmp_path):
    registry = tmp_path / "registry.json"
    registry.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "mirrors": [
                    {
                        "mirror_id": "agency",
                        "agency_id": "agency",
                        "handle": "agency-nz-arc.bsky.social",
                        "account_did": DID,
                        "handle_policy_version": 1,
                        "organisation_abbreviation": "agency",
                        "public_name": "Agency",
                        "jurisdiction": "nz",
                        "lifecycle_state": "live",
                        "environment": "bluesky-mirror-agency",
                        "profile_disclosure": "Unofficial automated archive mirror. Not Agency.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    report = tmp_path / "report.json"
    report.write_text(
        json.dumps(
            {
                "mirror_id": "agency",
                "cleanup_approval_packet": {
                    "requires_exact_uri_approval": True,
                    "candidates": [
                        {"uri": URI_ONE, "reasons": ["duplicate"]},
                        {"uri": URI_TWO, "reasons": ["excluded_source"]},
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
    return registry, report


def test_cleanup_dry_run_records_visibility_without_deleting(tmp_path) -> None:
    registry, report = write_inputs(tmp_path)
    deleted = []

    result = apply_cleanup(
        registry_path=registry,
        report_path=report,
        mirror_id="agency",
        approved_uris=[URI_ONE, URI_TWO],
        apply=False,
        visible_lookup=lambda _uris: {URI_ONE},
        deleter=lambda _account, uris: deleted.extend(uris),
    )

    assert result["status"] == "dry_run"
    assert result["visible_before_apply"] == [URI_ONE]
    assert result["already_missing"] == [URI_TWO]
    assert result["delete_requests_succeeded"] == []
    assert deleted == []


def test_cleanup_apply_deletes_only_visible_approved_uri(tmp_path) -> None:
    registry, report = write_inputs(tmp_path)
    deleted = []

    result = apply_cleanup(
        registry_path=registry,
        report_path=report,
        mirror_id="agency",
        approved_uris=[URI_ONE, URI_TWO],
        apply=True,
        visible_lookup=lambda _uris: {URI_ONE},
        deleter=lambda account, uris: deleted.append(
            (account["mirror_id"], uris)
        ),
    )

    assert result["status"] == "apply_completed"
    assert result["delete_requests_succeeded"] == [URI_ONE]
    assert deleted == [("agency", [URI_ONE])]


def test_cleanup_rejects_uri_absent_from_packet(tmp_path) -> None:
    registry, report = write_inputs(tmp_path)
    unknown = f"at://{DID}/app.bsky.feed.post/unknown"

    with pytest.raises(ValueError, match="absent from the cleanup packet"):
        apply_cleanup(
            registry_path=registry,
            report_path=report,
            mirror_id="agency",
            approved_uris=[unknown],
            apply=False,
        )


def test_cleanup_rejects_uri_owned_by_another_did(tmp_path) -> None:
    registry, report = write_inputs(tmp_path)
    wrong = "at://did:plc:other/app.bsky.feed.post/one"
    payload = json.loads(report.read_text(encoding="utf-8"))
    payload["cleanup_approval_packet"]["candidates"].append(
        {"uri": wrong, "reasons": ["duplicate"]}
    )
    report.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="not owned by the selected mirror DID"):
        apply_cleanup(
            registry_path=registry,
            report_path=report,
            mirror_id="agency",
            approved_uris=[wrong],
            apply=False,
        )


def test_cleanup_rejects_unapproved_visibility_result(tmp_path) -> None:
    registry, report = write_inputs(tmp_path)

    with pytest.raises(ValueError, match="unapproved URI"):
        apply_cleanup(
            registry_path=registry,
            report_path=report,
            mirror_id="agency",
            approved_uris=[URI_ONE],
            apply=False,
            visible_lookup=lambda _uris: {URI_TWO},
        )

def test_authenticated_delete_rejects_wrong_session_did(monkeypatch) -> None:
    monkeypatch.setenv("BLUESKY_HANDLE", "agency-nz-arc.bsky.social")
    monkeypatch.setenv("BLUESKY_APP_PASSWORD", "aaaa-bbbb-cccc-dddd")
    monkeypatch.setattr(
        cleanup,
        "_post_json",
        lambda *_args, **_kwargs: {
            "did": "did:plc:other",
            "accessJwt": "not-recorded",
        },
    )

    with pytest.raises(ValueError, match="Authenticated DID"):
        cleanup.authenticated_delete(
            {
                "handle": "agency-nz-arc.bsky.social",
                "account_did": DID,
            },
            [URI_ONE],
        )


def test_authenticated_delete_uses_exact_repo_collection_and_rkey(
    monkeypatch,
) -> None:
    monkeypatch.setenv("BLUESKY_HANDLE", "agency-nz-arc.bsky.social")
    monkeypatch.setenv("BLUESKY_APP_PASSWORD", "aaaa-bbbb-cccc-dddd")
    calls = []

    def fake_post(url, payload, *, access_token=""):
        calls.append((url, payload, access_token))
        if url.endswith("createSession"):
            return {"did": DID, "accessJwt": "not-recorded"}
        return {}

    monkeypatch.setattr(cleanup, "_post_json", fake_post)

    cleanup.authenticated_delete(
        {
            "handle": "agency-nz-arc.bsky.social",
            "account_did": DID,
        },
        [URI_ONE],
    )

    assert calls[1] == (
        "https://bsky.social/xrpc/com.atproto.repo.deleteRecord",
        {
            "repo": DID,
            "collection": "app.bsky.feed.post",
            "rkey": "one",
        },
        "not-recorded",
    )


def test_cleanup_script_supports_direct_execution() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(Path("scripts/apply_bluesky_mirror_cleanup.py")),
            "--help",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
