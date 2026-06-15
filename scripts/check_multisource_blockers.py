import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


EMAIL_CONFIG_PATH = Path("config/courts_nz_email_ingress.json")
LINKEDIN_DEFAULT_SEED = Path("imports/linkedin/courts-nz-linkedin-seed.json")
LINKEDIN_REPORT_PATH = Path("conductor/linkedin_archive_report.json")
LINKEDIN_NORMALIZED_ROOT = Path("historical_archive_normalized/linkedin")
PUBLICATION_REPORT_PATH = Path("conductor/archive_publication_report_20260614.json")


def check_multisource_blockers(
    env: dict[str, str] | None = None,
    secret_names: set[str] | None = None,
) -> dict[str, Any]:
    active_env = env if env is not None else dict(os.environ)
    active_secret_names = secret_names or set()
    checks = [
        _check_email_ingress(active_env, active_secret_names),
        _check_corpus_publication(active_env, active_secret_names),
        _check_linkedin_seed(),
    ]
    return {
        "complete": all(check["status"] == "complete" for check in checks),
        "checks": checks,
    }


def _check_email_ingress(env: dict[str, str], secret_names: set[str]) -> dict[str, Any]:
    config = _load_json(EMAIL_CONFIG_PATH)
    dedicated = config.get("dedicated_subscription_address", {})
    cloudflare_rule = dedicated.get("cloudflare_rule", {})
    domain_setup = config.get("domain_setup", {})
    cost_guardrail = config.get("cloudflare_cost_guardrail", {})
    fallback_routes = _fallback_route_statuses(config)
    status = str(dedicated.get("status") or "missing_config")
    capture_route_available = status == "active" or any(
        route["status"] == "active" for route in fallback_routes
    )
    required_secrets = [
        "CLOUDFLARE_API_TOKEN",
        "CLOUDFLARE_ACCOUNT_ID",
        "EMAIL_WORKER_GITHUB_TOKEN",
    ]
    missing = _missing_secret_names(required_secrets, env, secret_names)
    return {
        "id": "issue-5-email-ingress",
        "issue": "https://github.com/edithatogo/sm-govt-nz/issues/5",
        "status": "complete" if capture_route_available else "blocked",
        "dedicated_route_status": "complete" if status == "active" else "deferred",
        "configured_status": status,
        "address": dedicated.get("address", ""),
        "domain_status": domain_setup.get("status", "unknown"),
        "root_domain": domain_setup.get("root_domain", ""),
        "cloudflare_zone_status": domain_setup.get("cloudflare_zone_status", ""),
        "cloudflare_email_routing_enabled": domain_setup.get(
            "cloudflare_email_routing_enabled",
        ),
        "cloudflare_email_routing_status": domain_setup.get(
            "cloudflare_email_routing_status",
            "",
        ),
        "cloudflare_cli": domain_setup.get("cloudflare_cli", ""),
        "cloudflare_cli_version": domain_setup.get("cloudflare_cli_version", ""),
        "cloudflare_account_id": domain_setup.get("cloudflare_account_id", ""),
        "cloudflare_nameservers": domain_setup.get("cloudflare_nameservers", []),
        "cloudflare_rule_id": cloudflare_rule.get("id", ""),
        "cloudflare_rule_enabled": cloudflare_rule.get("enabled"),
        "cloudflare_rule_action": cloudflare_rule.get("action", ""),
        "cloudflare_rule_match": cloudflare_rule.get("match", ""),
        "cloudflare_rule_last_verified": cloudflare_rule.get("last_verified", ""),
        "cloudflare_cost_guardrail_status": cost_guardrail.get("status", "unknown"),
        "cloudflare_workers_plan": cost_guardrail.get("dashboard_observations", {}).get(
            "workers_plan",
            "",
        ),
        "cloudflare_billing_method": cost_guardrail.get("dashboard_observations", {}).get(
            "billing_method",
            "",
        ),
        "capture_route_available": capture_route_available,
        "active_fallback_routes": [
            route["provider"] for route in fallback_routes if route["status"] == "active"
        ],
        "fallback_routes": fallback_routes,
        "missing_secrets": missing,
        "next_action": (
            "Use the active manual Archive Email workflow dispatch route for zero-cost "
            "captures while the dedicated address is deferred. After explicit approval "
            "for any cost-bearing domain registration, register/delegate the root domain "
            "to the listed Cloudflare nameservers, rerun Cloudflare Email Routing with "
            "apply=true, subscribe the address to Courts of NZ judgments, then set the "
            "dedicated config status to active."
        ),
    }


def _check_corpus_publication(env: dict[str, str], secret_names: set[str]) -> dict[str, Any]:
    hf_missing = _missing_secret_names(["HF_TOKEN"], env, secret_names)
    zenodo_missing = _missing_secret_names(["ZENODO_TOKEN"], env, secret_names)
    report = _load_json(PUBLICATION_REPORT_PATH)
    hugging_face = report.get("hugging_face", {})
    zenodo = report.get("zenodo", {})
    hf_published = hugging_face.get("verified_status") == "200 OK"
    zenodo_status = str(zenodo.get("status") or "")
    zenodo_published = zenodo_status in {"published", "published_with_doi"}
    complete = hf_published and zenodo_published
    return {
        "id": "issue-6-corpus-publication",
        "issue": "https://github.com/edithatogo/sm-govt-nz/issues/6",
        "status": "complete" if complete else "blocked",
        "hugging_face_ready": not hf_missing,
        "hugging_face_published": hf_published,
        "zenodo_ready": not zenodo_missing,
        "zenodo_published": zenodo_published,
        "zenodo_status": zenodo_status or "missing_publication_report",
        "missing_hugging_face_secrets": hf_missing,
        "missing_zenodo_secrets": zenodo_missing,
        "hugging_face_repo_id": env.get("HF_DATASET_REPO_ID") or "inferred from token",
        "zenodo_endpoint": env.get("ZENODO_DEPOSIT_ENDPOINT")
        or env.get("ZENODO_DEPOSIT_API_URL")
        or "created from default depositions API",
        "sandbox_token_present": _has_secret(env, secret_names, "ZENODO_SANDBOX_TOKEN"),
        "next_action": (
            "Review and publish the Zenodo draft deposition, then update the publication "
            "report with the final Zenodo DOI/status."
        ),
    }


def _check_linkedin_seed() -> dict[str, Any]:
    seed_exists = LINKEDIN_DEFAULT_SEED.exists()
    report = _load_json(LINKEDIN_REPORT_PATH)
    record_count = int(report.get("record_count", 0) or 0)
    normalized_records = _count_jsonl_records(LINKEDIN_NORMALIZED_ROOT)
    complete = normalized_records > 0 and record_count > 0
    return {
        "id": "issue-7-linkedin-seed",
        "issue": "https://github.com/edithatogo/sm-govt-nz/issues/7",
        "status": "complete" if complete else "blocked",
        "default_seed_present": seed_exists,
        "report_record_count": record_count,
        "normalized_record_count": normalized_records,
        "next_action": (
            "Provide an approved archive-only LinkedIn seed JSON and run "
            "scripts/archive_linkedin_seed.py."
        ),
    }


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _count_jsonl_records(root: Path) -> int:
    if not root.exists():
        return 0
    total = 0
    for path in sorted(root.glob("*.jsonl")):
        total += sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    return total


def _fallback_route_statuses(config: dict[str, Any]) -> list[dict[str, str]]:
    routes = config.get("fallback_routes", [])
    if not isinstance(routes, list):
        return []
    statuses: list[dict[str, str]] = []
    for route in routes:
        if not isinstance(route, dict):
            continue
        statuses.append(
            {
                "provider": str(route.get("provider") or ""),
                "status": str(route.get("status") or "unknown"),
            }
        )
    return statuses


def _has_secret(env: dict[str, str], secret_names: set[str], name: str) -> bool:
    return bool(env.get(name)) or name in secret_names


def _missing_secret_names(
    required_names: list[str],
    env: dict[str, str],
    secret_names: set[str],
) -> list[str]:
    return [name for name in required_names if not _has_secret(env, secret_names, name)]


def _load_github_secret_names() -> set[str]:
    completed = subprocess.run(
        ["gh", "secret", "list"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        details = (completed.stderr or completed.stdout).strip()
        message = "Unable to list GitHub Actions secrets with gh."
        if details:
            message = f"{message} {details}"
        raise RuntimeError(message)
    names: set[str] = set()
    for line in completed.stdout.splitlines():
        parts = line.split()
        if parts:
            names.add(parts[0])
    return names


def write_markdown_report(report: dict[str, Any], path: str | Path) -> None:
    lines = ["# Multi-Source Archive Blocker Status", ""]
    for check in report["checks"]:
        lines.extend(
            [
                f"## {check['id']}",
                "",
                f"- Status: `{check['status']}`",
                f"- Issue: {check['issue']}",
                f"- Next action: {check['next_action']}",
                "",
            ]
        )
        for key, value in check.items():
            if key in {"id", "issue", "status", "next_action"}:
                continue
            lines.append(f"- {key}: `{json.dumps(value, sort_keys=True)}`")
        lines.append("")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Check multi-source archive blockers.")
    parser.add_argument("--json-output", default="")
    parser.add_argument("--markdown-output", default="")
    parser.add_argument(
        "--use-github-secrets",
        action="store_true",
        help="Treat names returned by gh secret list as present without exposing values.",
    )
    args = parser.parse_args()

    secret_names: set[str] = set()
    if args.use_github_secrets:
        try:
            secret_names = _load_github_secret_names()
        except RuntimeError as exc:
            print(f"warning: {exc}", file=sys.stderr)
    report = check_multisource_blockers(secret_names=secret_names)
    if args.json_output:
        Path(args.json_output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_output).write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if args.markdown_output:
        write_markdown_report(report, args.markdown_output)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
