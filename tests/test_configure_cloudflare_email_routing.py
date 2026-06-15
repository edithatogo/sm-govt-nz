import pytest

from scripts import configure_cloudflare_email_routing as routing


def test_domain_from_email_extracts_lowercase_domain() -> None:
    assert routing._domain_from_email("Courts@Archive.Example.TEST") == "archive.example.test"


def test_domain_from_email_rejects_invalid_address() -> None:
    with pytest.raises(ValueError):
        routing._domain_from_email("not-an-email")


def test_find_matching_rule_detects_existing_worker_rule() -> None:
    rule = {
        "id": "rule-id",
        "matchers": [{"type": "literal", "field": "to", "value": "courts@example.test"}],
        "actions": [{"type": "worker", "value": ["courts-worker"]}],
    }

    assert routing._find_matching_rule([rule], "courts@example.test", "courts-worker") == rule


def test_find_matching_rule_ignores_different_worker() -> None:
    rule = {
        "id": "rule-id",
        "matchers": [{"type": "literal", "field": "to", "value": "courts@example.test"}],
        "actions": [{"type": "worker", "value": ["other-worker"]}],
    }

    assert routing._find_matching_rule([rule], "courts@example.test", "courts-worker") is None


def test_configure_email_routing_reports_missing_zone(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(routing, "_find_zone", lambda config, zone_name: None)

    result = routing.configure_email_routing(
        email_address="courts@archive.example.test",
        worker_name="courts-worker",
        env={"CLOUDFLARE_ACCOUNT_ID": "account", "CLOUDFLARE_API_TOKEN": "token"},
    )

    assert result["status"] == "blocked_zone_not_found"
    assert result["zone_found"] is False


def test_configure_email_routing_dry_run_for_existing_zone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        routing,
        "_find_zone",
        lambda config, zone_name: {"id": "zone-id", "name": zone_name, "status": "active"},
    )
    monkeypatch.setattr(
        routing,
        "_request",
        lambda config, method, path, body=None, query=None: {
            "success": True,
            "result": {"enabled": False, "status": "unconfigured"},
        },
    )

    result = routing.configure_email_routing(
        email_address="courts@example.test",
        worker_name="courts-worker",
        env={"CLOUDFLARE_ACCOUNT_ID": "account", "CLOUDFLARE_API_TOKEN": "token"},
    )

    assert result["status"] == "dry_run_ready"
    assert result["zone_found"] is True
    assert result["routing_settings"]["result_status"] == "unconfigured"
