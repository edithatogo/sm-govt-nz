import json

from scripts import check_multisource_blockers as blockers


def test_check_multisource_blockers_reports_missing_external_inputs(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    write_json(
        tmp_path / "config" / "courts_nz_email_ingress.json",
        {
            "dedicated_subscription_address": {
                "status": "pending_external_setup",
                "address": "courts-nz-judgments@archive.edithatogo.com",
            }
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
    assert checks["issue-6-corpus-publication"]["missing_hugging_face_secrets"] == [
        "HF_DATASET_REPO_ID"
    ]
    assert checks["issue-6-corpus-publication"]["missing_zenodo_secrets"] == [
        "ZENODO_DEPOSIT_ENDPOINT"
    ]
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
