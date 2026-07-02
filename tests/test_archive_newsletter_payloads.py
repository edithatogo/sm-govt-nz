import json
from email.message import EmailMessage
from email.utils import format_datetime
from datetime import datetime, UTC

from scripts.archive_newsletter_payloads import archive_newsletter_payloads, load_newsletter_payloads


def newsletter_manifest(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "source_id": "agency-newsletter",
                        "agency_id": "agency",
                        "platform": "newsletter",
                        "source_type": "email_subscription",
                        "url": "mailto:newsletter@example.govt.nz",
                        "account": "Agency Newsletter",
                        "archive_status": "manual_seed",
                        "feasibility": "medium",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return manifest


def test_archive_newsletter_payloads_reports_missing_payload(tmp_path):
    report = archive_newsletter_payloads(
        manifest_path=newsletter_manifest(tmp_path),
        input_dir=tmp_path / "missing",
        raw_root=tmp_path / "raw" / "newsletter_email",
        normalized_root=tmp_path / "normalized" / "newsletter",
    )

    assert report["summary"]["status_counts"] == {"missing_payload": 1}
    assert report["results"][0]["status"] == "missing_payload"


def test_archive_newsletter_payloads_archives_json_payload(tmp_path):
    input_dir = tmp_path / "payloads"
    input_dir.mkdir()
    (input_dir / "payload.json").write_text(
        json.dumps(
            {
                "source_id": "agency-newsletter",
                "message_id": "<newsletter-1@example.govt.nz>",
                "from": "Agency <newsletter@example.govt.nz>",
                "to": "archive@example.test",
                "subject": "Agency update",
                "text": "Public newsletter body https://agency.example/newsletter/1",
                "received_at": "2026-07-01T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )

    report = archive_newsletter_payloads(
        manifest_path=newsletter_manifest(tmp_path),
        input_dir=input_dir,
        raw_root=tmp_path / "raw" / "newsletter_email",
        normalized_root=tmp_path / "normalized" / "newsletter",
    )

    assert report["summary"]["status_counts"] == {"captured": 1}
    normalized = tmp_path / "normalized" / "newsletter" / "2026-07.jsonl"
    record = json.loads(normalized.read_text(encoding="utf-8"))
    assert record["source_platform"] == "newsletter"
    assert record["source_kind"] == "email_subscription"
    assert record["canonical_url"] == "https://agency.example/newsletter/1"


def test_load_newsletter_payloads_accepts_eml(tmp_path):
    message = EmailMessage()
    message["Message-ID"] = "<eml-newsletter@example.govt.nz>"
    message["From"] = "Agency <newsletter@example.govt.nz>"
    message["To"] = "archive@example.test"
    message["Subject"] = "EML update"
    message["Date"] = format_datetime(datetime(2026, 7, 1, tzinfo=UTC))
    message.set_content("EML newsletter body")
    input_dir = tmp_path / "payloads"
    input_dir.mkdir()
    (input_dir / "payload.eml").write_bytes(message.as_bytes())

    payloads = load_newsletter_payloads(input_dir)

    assert len(payloads) == 1
    assert payloads[0]["message_id"] == "<eml-newsletter@example.govt.nz>"
    assert payloads[0]["subject"] == "EML update"
