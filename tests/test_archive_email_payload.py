import base64
import json

from scripts.archive_email_payload import archive_email_payload


def test_archive_email_payload_writes_raw_and_normalized_records(tmp_path) -> None:
    payload = {
        "message_id": "<judgment-1@example.test>",
        "from": "Courts of New Zealand <notices@example.test>",
        "to": "archive@example.test",
        "subject": "Judgment of public interest",
        "text": "A judgment is available at https://www.courtsofnz.govt.nz/cases/example",
        "received_at": "2026-06-14T01:02:03Z",
    }

    record = archive_email_payload(
        payload,
        raw_root=tmp_path / "historical_archive_raw" / "email",
        normalized_root=tmp_path / "historical_archive_normalized" / "email",
    )

    raw_path = tmp_path / record["raw_path"]
    normalized_path = tmp_path / "historical_archive_normalized" / "email" / "2026-06.jsonl"
    assert raw_path.exists()
    assert normalized_path.exists()
    assert record["source_platform"] == "email"
    assert record["canonical_url"] == "https://www.courtsofnz.govt.nz/cases/example"
    assert record["cross_source_ids"]["message_id"] == "<judgment-1@example.test>"

    lines = normalized_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    stored = json.loads(lines[0])
    assert stored["record_id"] == record["record_id"]


def test_archive_email_payload_is_idempotent_for_same_message_id(tmp_path) -> None:
    payload = {
        "message_id": "<same@example.test>",
        "subject": "First",
        "text": "Initial notice",
        "received_at": "2026-06-14T01:02:03Z",
    }
    archive_email_payload(
        payload,
        raw_root=tmp_path / "historical_archive_raw" / "email",
        normalized_root=tmp_path / "historical_archive_normalized" / "email",
    )
    normalized_path = tmp_path / "historical_archive_normalized" / "email" / "2026-06.jsonl"
    original_content = normalized_path.read_text(encoding="utf-8")
    archive_email_payload(
        payload,
        raw_root=tmp_path / "historical_archive_raw" / "email",
        normalized_root=tmp_path / "historical_archive_normalized" / "email",
    )
    assert normalized_path.read_text(encoding="utf-8") == original_content

    payload["text"] = "Updated notice"
    archive_email_payload(
        payload,
        raw_root=tmp_path / "historical_archive_raw" / "email",
        normalized_root=tmp_path / "historical_archive_normalized" / "email",
    )

    lines = normalized_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert "Updated notice" in json.loads(lines[0])["content"]


def test_archive_email_payload_accepts_raw_mime_base64(tmp_path) -> None:
    raw_mime = b"From: notices@example.test\nSubject: Raw notice\n\nBody"
    payload = {
        "message_id": "<raw@example.test>",
        "subject": "Raw notice",
        "text": "Body",
        "received_at": "2026-06-14T01:02:03Z",
        "raw_mime_base64": base64.b64encode(raw_mime).decode("ascii"),
    }

    record = archive_email_payload(
        payload,
        raw_root=tmp_path / "historical_archive_raw" / "email",
        normalized_root=tmp_path / "historical_archive_normalized" / "email",
    )

    assert (tmp_path / record["raw_path"]).read_bytes() == raw_mime
