import json
from subprocess import CompletedProcess

from scripts import check_multisource_blockers as blockers


def test_check_multisource_blockers_reports_missing_external_inputs(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    write_json(
        tmp_path / "config" / "courts_nz_email_ingress.json",
        {
            "dedicated_subscription_address": {
                "status": "pending_external_setup",
                "address": "courts-nz-judgments@archive.edithatogo.com",
            },
            "domain_setup": {
                "status": "pending_domain_registration_or_delegation",
                "root_domain": "edithatogo.com",
                "cloudflare_zone_status": "pending_nameserver_delegation",
                "cloudflare_nameservers": [
                    "jocelyn.ns.cloudflare.com",
                    "joel.ns.cloudflare.com",
                ],
            },
            "cloudflare_cost_guardrail": {
                "status": "active",
                "dashboard_observations": {
                    "workers_plan": "Free $0",
                    "billing_method": "no payment method on file",
                },
            },
        },
    )

    write_json(
        tmp_path / "conductor" / "archive_publication_report_20260614.json",
        {
            "hugging_face": {"verified_status": "200 OK"},
            "zenodo": {"status": "draft_uploaded_pending_review_and_publish"},
        },
    )

    report = blockers.check_multisource_blockers(env={"HF_TOKEN": "hf", "ZENODO_TOKEN": "zen"})

    assert report["complete"] is False
    checks = {check["id"]: check for check in report["checks"]}
    assert checks["issue-5-email-ingress"]["missing_secrets"] == [
        "CLOUDFLARE_API_TOKEN",
        "CLOUDFLARE_ACCOUNT_ID",
        "EMAIL_WORKER_GITHUB_TOKEN",
    ]
    assert (
        checks["issue-5-email-ingress"]["domain_status"]
        == "pending_domain_registration_or_delegation"
    )
    assert checks["issue-5-email-ingress"]["root_domain"] == "edithatogo.com"
    assert checks["issue-5-email-ingress"]["cloudflare_nameservers"] == [
        "jocelyn.ns.cloudflare.com",
        "joel.ns.cloudflare.com",
    ]
    assert checks["issue-5-email-ingress"]["cloudflare_cost_guardrail_status"] == "active"
    assert checks["issue-5-email-ingress"]["cloudflare_workers_plan"] == "Free $0"
    assert (
        checks["issue-5-email-ingress"]["cloudflare_billing_method"]
        == "no payment method on file"
    )
    assert checks["issue-6-corpus-publication"]["status"] == "blocked"
    assert checks["issue-6-corpus-publication"]["missing_hugging_face_secrets"] == []
    assert checks["issue-6-corpus-publication"]["missing_zenodo_secrets"] == []
    assert checks["issue-6-corpus-publication"]["hugging_face_published"] is True
    assert checks["issue-6-corpus-publication"]["zenodo_published"] is False
    assert (
        checks["issue-6-corpus-publication"]["zenodo_status"]
        == "draft_uploaded_pending_review_and_publish"
    )
    assert checks["issue-6-corpus-publication"]["hugging_face_repo_id"] == "inferred from token"
    assert (
        checks["issue-6-corpus-publication"]["zenodo_endpoint"]
        == "created from default depositions API"
    )
    assert checks["issue-7-linkedin-seed"]["status"] == "blocked"


def test_check_multisource_blockers_reports_complete_when_inputs_are_present(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    write_json(
        tmp_path / "config" / "courts_nz_email_ingress.json",
        {
            "dedicated_subscription_address": {
                "status": "active",
                "address": "courts-nz-judgments@archive.edithatogo.com",
            }
        },
    )
    write_json(tmp_path / "conductor" / "linkedin_archive_report.json", {"record_count": 1})
    write_json(
        tmp_path / "conductor" / "archive_publication_report_20260614.json",
        {
            "hugging_face": {"verified_status": "200 OK"},
            "zenodo": {"status": "published_with_doi", "doi": "10.5281/zenodo.123"},
        },
    )
    normalized = tmp_path / "historical_archive_normalized" / "linkedin" / "2026-06.jsonl"
    normalized.parent.mkdir(parents=True)
    normalized.write_text('{"record_id": "linkedin:1"}\n', encoding="utf-8")

    report = blockers.check_multisource_blockers(
        env={
            "CLOUDFLARE_API_TOKEN": "cf",
            "CLOUDFLARE_ACCOUNT_ID": "account",
            "EMAIL_WORKER_GITHUB_TOKEN": "gh",
            "HF_TOKEN": "hf",
            "HF_DATASET_REPO_ID": "org/dataset",
            "ZENODO_TOKEN": "zen",
            "ZENODO_DEPOSIT_ENDPOINT": "https://zenodo.example/api/deposit/depositions/1/files",
        }
    )

    assert report["complete"] is True
    assert {check["status"] for check in report["checks"]} == {"complete"}


def test_check_multisource_blockers_uses_github_secret_presence(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    write_json(
        tmp_path / "config" / "courts_nz_email_ingress.json",
        {
            "dedicated_subscription_address": {
                "status": "active",
                "address": "courts-nz-judgments@archive.edithatogo.com",
            }
        },
    )
    write_json(tmp_path / "conductor" / "linkedin_archive_report.json", {"record_count": 1})
    write_json(
        tmp_path / "conductor" / "archive_publication_report_20260614.json",
        {
            "hugging_face": {"verified_status": "200 OK"},
            "zenodo": {"status": "published_with_doi", "doi": "10.5281/zenodo.123"},
        },
    )
    normalized = tmp_path / "historical_archive_normalized" / "linkedin" / "2026-06.jsonl"
    normalized.parent.mkdir(parents=True)
    normalized.write_text('{"record_id": "linkedin:1"}\n', encoding="utf-8")

    report = blockers.check_multisource_blockers(
        env={},
        secret_names={
            "CLOUDFLARE_API_TOKEN",
            "CLOUDFLARE_ACCOUNT_ID",
            "EMAIL_WORKER_GITHUB_TOKEN",
            "HF_TOKEN",
            "ZENODO_TOKEN",
            "ZENODO_SANDBOX_TOKEN",
        },
    )

    checks = {check["id"]: check for check in report["checks"]}
    assert report["complete"] is True
    assert checks["issue-5-email-ingress"]["missing_secrets"] == []
    assert checks["issue-6-corpus-publication"]["missing_hugging_face_secrets"] == []
    assert checks["issue-6-corpus-publication"]["missing_zenodo_secrets"] == []
    assert checks["issue-6-corpus-publication"]["sandbox_token_present"] is True


def test_load_github_secret_names_parses_gh_output(monkeypatch) -> None:
    def fake_run(args, check, capture_output, text):
        assert args == ["gh", "secret", "list"]
        assert check is False
        assert capture_output is True
        assert text is True
        return CompletedProcess(
            args=args,
            returncode=0,
            stdout="HF_TOKEN 2026-06-15T00:00:00Z\nZENODO_TOKEN 2026-06-15T00:00:00Z\n",
            stderr="",
        )

    monkeypatch.setattr(blockers.subprocess, "run", fake_run)

    assert blockers._load_github_secret_names() == {"HF_TOKEN", "ZENODO_TOKEN"}


def test_main_falls_back_when_github_secret_listing_is_forbidden(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        ["check_multisource_blockers.py", "--use-github-secrets"],
    )
    write_json(
        tmp_path / "config" / "courts_nz_email_ingress.json",
        {"dedicated_subscription_address": {"status": "pending_external_setup"}},
    )

    def fake_run(args, check, capture_output, text):
        return CompletedProcess(
            args=args,
            returncode=1,
            stdout="",
            stderr=(
                "failed to get secrets: HTTP 403: "
                "Resource not accessible by integration"
            ),
        )

    monkeypatch.setattr(blockers.subprocess, "run", fake_run)

    blockers.main()

    captured = capsys.readouterr()
    assert "warning: Unable to list GitHub Actions secrets with gh." in captured.err
    assert '"complete": false' in captured.out


def test_write_markdown_report(tmp_path) -> None:
    path = tmp_path / "report.md"
    blockers.write_markdown_report(
        {
            "complete": False,
            "checks": [
                {
                    "id": "issue-5-email-ingress",
                    "issue": "https://example.test/5",
                    "status": "blocked",
                    "next_action": "Do setup.",
                    "missing_secrets": ["TOKEN"],
                }
            ],
        },
        path,
    )

    assert "issue-5-email-ingress" in path.read_text(encoding="utf-8")


def write_json(path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
