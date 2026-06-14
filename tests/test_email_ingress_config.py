import json
from pathlib import Path


def test_email_ingress_config_documents_default_and_fallback_routes() -> None:
    config = json.loads(Path("config/courts_nz_email_ingress.json").read_text(encoding="utf-8"))

    assert config["agency_id"] == "courts-nz"
    assert config["archive_only"] is True
    assert config["dedicated_subscription_address"]["status"] == "pending_external_setup"
    assert config["dedicated_subscription_address"]["address"].startswith("courts-nz-judgments@")
    assert config["dedicated_subscription_address"]["tracking_issue"].endswith("/issues/5")
    assert config["default_route"]["provider"] == "cloudflare_email_routing_worker"
    assert config["default_route"]["repository_dispatch_event_type"] == "courts_nz_email_received"
    assert [route["provider"] for route in config["fallback_routes"]] == [
        "mailgun_inbound_parse",
        "scheduled_mailbox_polling",
    ]


def test_email_ingress_config_preserves_archive_only_guardrails() -> None:
    config = json.loads(Path("config/courts_nz_email_ingress.json").read_text(encoding="utf-8"))
    guardrails = config["guardrails"]

    assert guardrails["must_not_post_to_mirrors"] is True
    assert guardrails["must_not_advance_outbound_state"] is True
    assert guardrails["must_store_raw_before_normalized"] is True
    assert set(guardrails["dedupe_keys"]) == {"message_id", "canonical_url", "content_hash"}
