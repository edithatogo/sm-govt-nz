import argparse
import json

from scripts.build_manual_seed_onboarding_report import build_report, build_work_queue, write_summary


def test_manual_seed_onboarding_report_marks_missing_and_present_seeds(tmp_path):
    manifest = tmp_path / "manifest.json"
    policy = tmp_path / "policy.json"
    seed_root = tmp_path / "manual_archive_seeds"
    report_path = tmp_path / "report.json"
    manifest.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "source_id": "agency-facebook",
                        "agency_id": "agency",
                        "agency_name": "Agency",
                        "platform": "facebook",
                        "source_type": "social_profile",
                        "url": "https://facebook.com/agency",
                        "account": "Agency",
                        "archive_status": "candidate",
                        "feasibility": "medium",
                    },
                    {
                        "source_id": "agency-linkedin",
                        "agency_id": "agency",
                        "agency_name": "Agency",
                        "platform": "linkedin",
                        "source_type": "social_profile",
                        "url": "https://linkedin.com/company/agency",
                        "account": "Agency",
                        "archive_status": "manual_seed",
                        "feasibility": "low",
                    },
                    {
                        "source_id": "agency-youtube",
                        "agency_id": "agency",
                        "platform": "youtube",
                        "source_type": "social_profile",
                        "url": "https://youtube.com/@agency",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    policy.write_text(
        json.dumps(
            {
                "platforms": {
                    "facebook": {
                        "acceptable_access_methods": ["meta_graph_api", "operator_authorized_seed"],
                        "required_authorization": "page_owner_or_approved_app",
                        "seed_directory": str(seed_root / "facebook"),
                        "seed_schema": "posts[]",
                        "live_capture_policy": "no public scraping",
                    },
                    "linkedin": {
                        "acceptable_access_methods": ["approved_linkedin_api", "operator_authorized_seed"],
                        "required_authorization": "organization_admin_or_approved_app",
                        "seed_directory": str(seed_root / "linkedin"),
                        "seed_schema": "posts[]",
                        "live_capture_policy": "no public automation",
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    seed_dir = seed_root / "linkedin"
    seed_dir.mkdir(parents=True)
    (seed_dir / "agency-linkedin.json").write_text('{"posts": []}', encoding="utf-8")

    report = build_report(
        argparse.Namespace(
            manifest=manifest,
            policy=policy,
            report=report_path,
            manual_seed_root=seed_root,
            platforms="facebook,linkedin",
        )
    )

    assert report["summary"]["selected_sources"] == 2
    assert report["summary"]["status_counts"] == {
        "needs_authorized_seed_or_api": 1,
        "seed_present": 1,
    }
    assert report["summary"]["remaining_groups"] == {"facebook": 1}
    assert report["summary"]["remaining_group_count"] == 1
    assert report["summary"]["remaining_source_count"] == 1
    by_platform = {item["platform"]: item for item in report["items"]}
    assert by_platform["facebook"]["onboarding_status"] == "needs_authorized_seed_or_api"
    assert by_platform["linkedin"]["onboarding_status"] == "seed_present"
    assert by_platform["facebook"]["preferred_seed_path"].endswith("/facebook/agency-facebook.json")
    assert "meta_graph_api" in by_platform["facebook"]["acceptable_access_methods"]
    assert by_platform["facebook"]["live_capture_policy"] == "no public scraping"

    queue = build_work_queue(report)
    assert queue["summary"]["queue_count"] == 1
    assert queue["summary"]["platform_counts"] == {"facebook": 1}
    assert queue["items"][0]["source_id"] == "agency-facebook"
    assert queue["items"][0]["preferred_seed_path"].endswith("/facebook/agency-facebook.json")


def test_manual_seed_onboarding_report_writes_summary(tmp_path):
    manifest = tmp_path / "manifest.json"
    policy = tmp_path / "policy.json"
    summary_path = tmp_path / "summary.md"
    manifest.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "source_id": "agency-facebook",
                        "agency_id": "agency",
                        "agency_name": "Agency",
                        "platform": "facebook",
                        "source_type": "social_profile",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    policy.write_text(json.dumps({"platforms": {"facebook": {"seed_directory": "manual_archive_seeds/facebook"}}}), encoding="utf-8")

    report = build_report(
        argparse.Namespace(
            manifest=manifest,
            policy=policy,
            report=tmp_path / "report.json",
            manual_seed_root=tmp_path / "manual_archive_seeds",
            platforms="facebook",
        )
    )

    write_summary(summary_path, report)
    assert summary_path.is_file()
    summary = summary_path.read_text(encoding="utf-8")
    assert "Remaining groups" in summary
    assert "`facebook`: 1" in summary
    assert report["summary"]["remaining_group_count"] == 1


def test_manual_seed_onboarding_report_is_limited_to_requested_platforms(tmp_path):
    manifest = tmp_path / "manifest.json"
    policy = tmp_path / "policy.json"
    manifest.write_text(
        json.dumps(
            {
                "sources": [
                    {"source_id": "one", "agency_id": "a", "platform": "facebook"},
                    {"source_id": "two", "agency_id": "a", "platform": "instagram"},
                    {"source_id": "three", "agency_id": "a", "platform": "x"},
                ]
            }
        ),
        encoding="utf-8",
    )
    policy.write_text(
        json.dumps(
            {
                "platforms": {
                    "facebook": {"seed_directory": "manual_archive_seeds/facebook"},
                    "instagram": {"seed_directory": "manual_archive_seeds/instagram"},
                    "x": {"seed_directory": "manual_archive_seeds/x"},
                }
            }
        ),
        encoding="utf-8",
    )

    report = build_report(
        argparse.Namespace(
            manifest=manifest,
            policy=policy,
            report=tmp_path / "report.json",
            manual_seed_root=tmp_path / "manual_archive_seeds",
            platforms="facebook,x",
        )
    )

    assert report["summary"]["platform_counts"] == {"facebook": 1, "x": 1}
    assert {item["platform"] for item in report["items"]} == {"facebook", "x"}


def test_manual_seed_onboarding_report_includes_newsletter_policy(tmp_path):
    manifest = tmp_path / "manifest.json"
    policy = tmp_path / "policy.json"
    manifest.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "source_id": "agency-newsletter",
                        "agency_id": "agency",
                        "platform": "newsletter",
                        "source_type": "newsletter",
                        "url": "https://agency.example/newsletter",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    policy.write_text(
        json.dumps(
            {
                "platforms": {
                    "newsletter": {
                        "acceptable_access_methods": ["public_newsletter_archive", "operator_authorized_seed"],
                        "required_authorization": "public_archive_or_operator_authorized_capture",
                        "seed_directory": "manual_archive_seeds/newsletter",
                        "seed_schema": "posts[]",
                        "live_capture_policy": "public archive or authorized seed only",
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    report = build_report(
        argparse.Namespace(
            manifest=manifest,
            policy=policy,
            report=tmp_path / "report.json",
            manual_seed_root=tmp_path / "manual_archive_seeds",
            platforms="newsletter",
        )
    )

    assert report["summary"]["platform_counts"] == {"newsletter": 1}
    assert report["items"][0]["onboarding_status"] == "needs_authorized_seed_or_api"
    assert "public_newsletter_archive" in report["items"][0]["acceptable_access_methods"]


def test_manual_seed_work_queue_orders_lowest_friction_platforms_first(tmp_path):
    manifest = tmp_path / "manifest.json"
    policy = tmp_path / "policy.json"
    manifest.write_text(
        json.dumps(
            {
                "sources": [
                    {"source_id": "fb", "agency_id": "b", "agency_name": "B", "platform": "facebook"},
                    {"source_id": "threads", "agency_id": "a", "agency_name": "A", "platform": "threads"},
                    {"source_id": "newsletter", "agency_id": "c", "agency_name": "C", "platform": "newsletter"},
                ]
            }
        ),
        encoding="utf-8",
    )
    policy.write_text(
        json.dumps(
            {
                "platforms": {
                    "facebook": {"seed_directory": "manual_archive_seeds/facebook"},
                    "threads": {"seed_directory": "manual_archive_seeds/threads"},
                    "newsletter": {"seed_directory": "manual_archive_seeds/newsletter"},
                }
            }
        ),
        encoding="utf-8",
    )

    report = build_report(
        argparse.Namespace(
            manifest=manifest,
            policy=policy,
            report=tmp_path / "report.json",
            manual_seed_root=tmp_path / "manual_archive_seeds",
            platforms="facebook,threads,newsletter",
        )
    )

    queue = build_work_queue(report)

    assert queue["summary"]["priority_order"] == ["threads", "newsletter", "facebook"]
    assert [item["source_id"] for item in queue["items"]] == ["threads", "newsletter", "fb"]
