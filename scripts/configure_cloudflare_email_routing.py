import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


API_BASE = "https://api.cloudflare.com/client/v4"


@dataclass(frozen=True)
class CloudflareConfig:
    account_id: str
    api_token: str


def configure_email_routing(
    *,
    email_address: str,
    worker_name: str,
    zone_name: str | None = None,
    create_zone: bool = False,
    apply: bool = False,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    active_env = env if env is not None else dict(os.environ)
    config = CloudflareConfig(
        account_id=_required_env(active_env, "CLOUDFLARE_ACCOUNT_ID"),
        api_token=_required_env(active_env, "CLOUDFLARE_API_TOKEN"),
    )
    email_domain = _domain_from_email(email_address)
    target_zone_name = zone_name or email_domain

    exact_zone = _find_zone(config, target_zone_name)
    fallback_zone = None
    if exact_zone is None and target_zone_name != email_domain:
        fallback_zone = _find_zone(config, email_domain)
    if exact_zone is None and fallback_zone is None and email_domain.count(".") >= 2:
        fallback_zone = _find_zone(config, ".".join(email_domain.split(".")[-2:]))

    zone = exact_zone or fallback_zone
    created_zone_response = None
    if zone is None and create_zone:
        created_zone_response = _create_zone(config, target_zone_name)
        if _success(created_zone_response):
            zone = created_zone_response.get("result")

    result: dict[str, Any] = {
        "apply": apply,
        "create_zone": create_zone,
        "email_address": email_address,
        "email_domain": email_domain,
        "requested_zone_name": target_zone_name,
        "worker_name": worker_name,
        "zone_found": bool(zone),
    }
    if created_zone_response is not None:
        result["create_zone_response"] = _zone_summary(created_zone_response)

    if zone is None:
        result["status"] = "blocked_zone_not_found"
        result["next_action"] = (
            f"Onboard {target_zone_name} or a parent zone for {email_domain} "
            "in Cloudflare, then rerun this workflow."
        )
        return result

    result["zone_name"] = zone.get("name")
    result["zone_status"] = zone.get("status")
    result["zone_name_servers"] = zone.get("name_servers") or []
    if created_zone_response is not None:
        result["status"] = "zone_created_pending_nameserver_delegation"
        result["next_action"] = (
            "Delegate the listed Cloudflare nameservers at the current DNS host, "
            "then rerun with apply=true after the zone becomes active."
        )
        return result

    zone_id = str(zone["id"])
    routing_settings = _request(config, "GET", f"/zones/{zone_id}/email/routing")
    result["routing_settings"] = _summary(routing_settings)

    if not apply:
        result["status"] = "dry_run_ready"
        result["next_action"] = "Rerun with apply=true to enable routing and create the Worker rule."
        return result

    if not _success(routing_settings) or not routing_settings.get("result", {}).get("enabled"):
        enable_response = _request(config, "POST", f"/zones/{zone_id}/email/routing/enable", {})
        result["enable_response"] = _summary(enable_response)
        if not _success(enable_response):
            result["status"] = "blocked_enable_failed"
            return result

    rules_response = _request(config, "GET", f"/zones/{zone_id}/email/routing/rules")
    result["rules_response"] = _summary(rules_response)
    if not _success(rules_response):
        result["status"] = "blocked_list_rules_failed"
        return result

    existing_rule = _find_matching_rule(rules_response.get("result", []), email_address, worker_name)
    if existing_rule:
        result["status"] = "active"
        result["rule_id"] = existing_rule.get("id")
        result["rule_already_present"] = True
        return result

    payload = {
        "actions": [{"type": "worker", "value": [worker_name]}],
        "matchers": [{"type": "literal", "field": "to", "value": email_address}],
        "enabled": True,
        "name": f"Archive {email_address} via {worker_name}",
        "priority": 0,
    }
    create_response = _request(config, "POST", f"/zones/{zone_id}/email/routing/rules", payload)
    result["create_response"] = _summary(create_response)
    if not _success(create_response):
        result["status"] = "blocked_create_rule_failed"
        return result

    result["status"] = "active"
    result["rule_id"] = create_response.get("result", {}).get("id")
    return result


def _required_env(env: dict[str, str], name: str) -> str:
    value = env.get(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _domain_from_email(email_address: str) -> str:
    if "@" not in email_address:
        raise ValueError(f"Email address must contain @: {email_address}")
    return email_address.rsplit("@", 1)[1].strip().lower()


def _find_zone(config: CloudflareConfig, zone_name: str) -> dict[str, Any] | None:
    response = _request(
        config,
        "GET",
        "/zones",
        query={"name": zone_name, "account.id": config.account_id},
    )
    if not _success(response):
        raise RuntimeError(json.dumps(_summary(response), sort_keys=True))
    zones = response.get("result", [])
    if not zones:
        return None
    return zones[0]


def _create_zone(config: CloudflareConfig, zone_name: str) -> dict[str, Any]:
    return _request(
        config,
        "POST",
        "/zones",
        {
            "account": {"id": config.account_id},
            "name": zone_name,
            "type": "full",
        },
    )


def _find_matching_rule(
    rules: list[dict[str, Any]],
    email_address: str,
    worker_name: str,
) -> dict[str, Any] | None:
    for rule in rules:
        matchers = rule.get("matchers") or []
        actions = rule.get("actions") or []
        matches_email = any(
            matcher.get("type") == "literal"
            and matcher.get("field") == "to"
            and str(matcher.get("value", "")).lower() == email_address.lower()
            for matcher in matchers
        )
        routes_to_worker = any(
            action.get("type") == "worker"
            and worker_name in [str(value) for value in action.get("value", [])]
            for action in actions
        )
        if matches_email and routes_to_worker:
            return rule
    return None


def _request(
    config: CloudflareConfig,
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    query: dict[str, str] | None = None,
) -> dict[str, Any]:
    encoded_query = f"?{urllib.parse.urlencode(query)}" if query else ""
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        f"{API_BASE}{path}{encoded_query}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {config.api_token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        payload = error.read().decode("utf-8")
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return {"success": False, "errors": [{"code": error.code, "message": payload}]}


def _success(response: dict[str, Any]) -> bool:
    return bool(response.get("success"))


def _summary(response: dict[str, Any]) -> dict[str, Any]:
    result = response.get("result")
    return {
        "success": _success(response),
        "errors": [
            {"code": error.get("code"), "message": error.get("message")}
            for error in response.get("errors", [])
        ],
        "messages": [
            {"code": message.get("code"), "message": message.get("message")}
            for message in response.get("messages", [])
        ],
        "result_status": result.get("status") if isinstance(result, dict) else None,
        "result_enabled": result.get("enabled") if isinstance(result, dict) else None,
    }


def _zone_summary(response: dict[str, Any]) -> dict[str, Any]:
    result = response.get("result") if isinstance(response.get("result"), dict) else {}
    summary = _summary(response)
    summary.update(
        {
            "zone_name": result.get("name"),
            "zone_status": result.get("status"),
            "zone_name_servers": result.get("name_servers") or [],
        }
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Configure Cloudflare Email Routing to a Worker.")
    parser.add_argument("--email-address", required=True)
    parser.add_argument("--worker-name", required=True)
    parser.add_argument("--zone-name")
    parser.add_argument("--create-zone", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    result = configure_email_routing(
        email_address=args.email_address,
        worker_name=args.worker_name,
        zone_name=args.zone_name,
        create_zone=args.create_zone,
        apply=args.apply,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    if not args.apply:
        raise SystemExit(0)
    raise SystemExit(0 if result["status"] == "active" else 1)


if __name__ == "__main__":
    main()
