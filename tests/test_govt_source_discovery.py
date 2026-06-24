import argparse
import json

from scripts.discover_govt_source_candidates import build_report


def test_discovery_builds_candidate_report_and_archive_manifest(tmp_path):
    registry = tmp_path / "registry.json"
    config = tmp_path / "config.json"
    registry.write_text(
        json.dumps(
            [
                {
                    "agency_id": "agency-one",
                    "name": "Agency One",
                    "type": "Department",
                    "portfolio": "Test",
                    "official_website": "https://agency.example",
                    "status": "active",
                    "social_profiles": {
                        "bluesky": {
                            "handle": "agency.bsky.social",
                            "url": "https://bsky.app/profile/agency.bsky.social",
                            "status": "active",
                        },
                        "linkedin": {
                            "handle": "Agency One",
                            "url": "https://www.linkedin.com/company/agency-one",
                            "status": "active",
                        },
                    },
                },
                {
                    "agency_id": "agency-two",
                    "name": "Agency Two",
                    "official_website": "https://two.example",
                    "social_profiles": {},
                },
            ]
        ),
        encoding="utf-8",
    )
    config.write_text(
        json.dumps(
            {
                "homepage_probe": {"common_paths": ["/", "/news"]},
                "platform_archive_policy": {
                    "bluesky": {
                        "feasibility": "high",
                        "archive_status": "ready",
                        "access_method": "public_at_protocol",
                        "auth": "none",
                    },
                    "linkedin": {
                        "feasibility": "low",
                        "archive_status": "manual_seed",
                        "access_method": "approved_api",
                        "auth": "operator_authorized",
                    },
                    "rss": {
                        "feasibility": "high",
                        "archive_status": "ready",
                        "access_method": "public_rss",
                        "auth": "none",
                    },
                    "website_page": {
                        "feasibility": "high",
                        "archive_status": "ready",
                        "access_method": "bounded_public_html",
                        "auth": "none",
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    report, manifest = build_report(
        argparse.Namespace(
            registry=registry,
            config=config,
            probe_homepages=False,
            max_agencies=0,
        )
    )

    assert report["summary"]["agency_count"] == 2
    assert report["summary"]["agencies_without_social_profiles"] == 1
    assert report["summary"]["known_registry_social_profiles"] == 2
    assert report["summary"]["platform_counts"]["bluesky"] == 1
    assert report["summary"]["source_type_counts"]["search_seed"] == 2
    assert manifest["summary"]["archive_status_counts"]["ready"] == 3
    assert manifest["summary"]["archive_status_counts"]["manual_seed"] == 1
    assert all(source["source_type"] != "search_seed" for source in manifest["sources"])
