import json
from pathlib import Path


def test_email_ingress_config_documents_default_and_fallback_routes() -> None:
    config = json.loads(Path("config/courts_nz_email_ingress.json").read_text(encoding="utf-8"))

    assert config["agency_id"] == "courts-nz"
    assert config["archive_only"] is True
    assert config["dedicated_subscription_address"]["status"] == "pending_external_setup"
    assert config["dedicated_subscription_address"]["address"].startswith("courts-nz-judgments@")
    assert config["dedicated_subscription_address"]["tracking_issue"].endswith("/issues/5")
    rule = config["dedicated_subscription_address"]["cloudflare_rule"]
    assert rule["id"] == "4fbe93480e834fd786a1959020c8a526"
    assert rule["enabled"] is False
    assert rule["match"] == "to:courts-nz-judgments@archive.edithatogo.com"
    assert rule["action"] == "worker:courts-nz-email-archive"
    assert config["domain_setup"]["root_domain"] == "edithatogo.com"
    assert config["domain_setup"]["status"] == "pending_domain_registration_or_delegation"
    assert config["domain_setup"]["cloudflare_zone_status"] == "email_routing_unconfigured"
    assert config["domain_setup"]["cloudflare_email_routing_enabled"] is False
    assert config["domain_setup"]["cloudflare_email_routing_status"] == "unconfigured"
    assert config["domain_setup"]["cloudflare_cli"] == "npx -y wrangler"
    assert config["domain_setup"]["cloudflare_cli_version"] == "4.100.0"
    assert config["domain_setup"]["cloudflare_nameservers"] == [
        "jocelyn.ns.cloudflare.com",
        "joel.ns.cloudflare.com",
    ]
    guardrail = config["cloudflare_cost_guardrail"]
    assert guardrail["status"] == "active"
    assert guardrail["dashboard_observations"]["workers_plan"] == "Free $0"
    assert guardrail["dashboard_observations"]["billing_method"] == "no payment method on file"
    assert guardrail["must_not_add_payment_method"] is True
    assert guardrail["must_not_register_domain_without_explicit_approval"] is True
    assert config["default_route"]["provider"] == "cloudflare_email_routing_worker"
    assert config["default_route"]["repository_dispatch_event_type"] == "courts_nz_email_received"
    assert [route["provider"] for route in config["fallback_routes"]] == [
        "pipedream_email_trigger",
        "manual_workflow_dispatch",
        "mailgun_inbound_parse",
        "scheduled_mailbox_polling",
    ]
    pipedream_route = config["fallback_routes"][0]
    assert pipedream_route["status"] == "recommended_zero_cost_automation"
    assert pipedream_route["cost"].startswith("$0 expected")
    assert pipedream_route["usage_assessment"]["risk_of_paid_usage"].startswith("low")
    manual_route = config["fallback_routes"][1]
    assert manual_route["status"] == "active"
    assert manual_route["workflow"] == "Archive Email"
    assert manual_route["cost"] == "$0"


def test_email_ingress_config_preserves_archive_only_guardrails() -> None:
    config = json.loads(Path("config/courts_nz_email_ingress.json").read_text(encoding="utf-8"))
    guardrails = config["guardrails"]

    assert guardrails["must_not_post_to_mirrors"] is True
    assert guardrails["must_not_advance_outbound_state"] is True
    assert guardrails["must_store_raw_before_normalized"] is True
    assert set(guardrails["dedupe_keys"]) == {"message_id", "canonical_url", "content_hash"}
