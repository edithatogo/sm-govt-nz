import argparse
import json
import os
from pathlib import Path
from typing import Any


EMAIL_CONFIG_PATH = Path("config/courts_nz_email_ingress.json")
LINKEDIN_DEFAULT_SEED = Path("imports/linkedin/courts-nz-linkedin-seed.json")
LINKEDIN_REPORT_PATH = Path("conductor/linkedin_archive_report.json")
LINKEDIN_NORMALIZED_ROOT = Path("historical_archive_normalized/linkedin")
PUBLICATION_REPORT_PATH = Path("conductor/archive_publication_report_20260614.json")


def check_multisource_blockers(env: dict[str, str] | None = None) -> dict[str, Any]:
    active_env = env if env is not None else dict(os.environ)
    checks = [
        _check_email_ingress(active_env),
        _check_corpus_publication(active_env),
        _check_linkedin_seed(),
    ]
    return {
        "complete": all(check["status"] == "complete" for check in checks),
        "checks": checks,
    }


def _check_email_ingress(env: dict[str, str]) -> dict[str, Any]:
    config = _load_json(EMAIL_CONFIG_PATH)
    dedicated = config.get("dedicated_subscription_address", {})
    status = str(dedicated.get("status") or "missing_config")
    required_secrets = [
        "CLOUDFLARE_API_TOKEN",
        "CLOUDFLARE_ACCOUNT_ID",
        "EMAIL_WORKER_GITHUB_TOKEN",
    ]
    missing = [name for name in required_secrets if not env.get(name)]
    return {
        "id": "issue-5-email-ingress",
        "issue": "https://github.com/edithatogo/sm-govt-nz/issues/5",
        "status": "complete" if status == "active" else "blocked",
        "configured_status": status,
        "address": dedicated.get("address", ""),
        "missing_secrets": missing,
        "next_action": (
            "Deploy the Cloudflare Email Routing Worker, route the address to it, "
            "subscribe the address to Courts of NZ judgments, then set the config status to active."
        ),
    }


def _check_corpus_publication(env: dict[str, str]) -> dict[str, Any]:
    hf_missing = [name for name in ["HF_TOKEN"] if not env.get(name)]
    zenodo_missing = [name for name in ["ZENODO_TOKEN"] if not env.get(name)]
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
        "sandbox_token_present": bool(env.get("ZENODO_SANDBOX_TOKEN")),
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
    args = parser.parse_args()

    report = check_multisource_blockers()
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
