import argparse
import json
from pathlib import Path

from scripts.discover_govt_source_candidates import (
    build_report,
    detect_platform,
    looks_like_json_feed_url,
    looks_like_public_newsletter_archive,
    summarize,
)


def test_discovery_recognizes_public_json_feeds_and_newsletter_archives() -> None:
    assert looks_like_json_feed_url(
        "https://agency.example/updates.json",
        "News feed",
        "application/json",
    )
    assert looks_like_public_newsletter_archive(
        "https://agency.example/newsletters",
        "Past issues",
    )
    assert looks_like_public_newsletter_archive(
        "https://agency.createsend.com/t/ViewEmailArchive/r/123",
        "Email archive",
    )


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


def test_discovery_summary_matches_compact_report_shape(tmp_path):
    registry = tmp_path / "registry.json"
    config = tmp_path / "config.json"
    registry.write_text(
        json.dumps(
            [
                {
                    "agency_id": "agency-one",
                    "name": "Agency One",
                    "social_profiles": {
                        "rss": {
                            "url": "https://agency.example/feed.xml",
                            "status": "active",
                        }
                    },
                }
            ]
        ),
        encoding="utf-8",
    )
    config.write_text(
        json.dumps(
            {
                "homepage_probe": {"common_paths": ["/"]},
                "platform_archive_policy": {
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
    summary = summarize(report, manifest)

    assert summary.startswith("# Government Source Discovery Summary\n")
    assert "- Candidate records: 1" in summary
    assert "- Archive manifest sources: 1" in summary
    assert "conductor/govt_source_candidate_report.json" in summary


def test_discovery_detects_medium_and_substack_platforms():
    assert detect_platform("https://nzdefenceforce.medium.com") == "medium"
    assert detect_platform("https://example.substack.com") == "substack"


def test_discovery_workflow_commits_summary_artifact():
    workflow = Path(".github/workflows/govt_source_discovery.yml").read_text(encoding="utf-8")

    assert "conductor/govt_source_candidate_summary.md" in workflow
    assert "Commit discovery updates" in workflow


def test_discovery_preserves_existing_manual_manifest_sources(tmp_path):
    registry = tmp_path / "registry.json"
    config = tmp_path / "config.json"
    manifest_path = tmp_path / "manifest.json"
    registry.write_text(
        json.dumps(
            [
                {
                    "agency_id": "agency-one",
                    "name": "Agency One",
                    "official_website": "https://agency.example",
                    "social_profiles": {},
                }
            ]
        ),
        encoding="utf-8",
    )
    config.write_text(
        json.dumps(
            {
                "homepage_probe": {"common_paths": ["/"]},
                "platform_archive_policy": {
                    "website_page": {
                        "feasibility": "high",
                        "archive_status": "ready",
                        "access_method": "bounded_public_html",
                        "auth": "none",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    manifest_path.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "source_id": "agency-one-newsletter-manual",
                        "agency_id": "agency-one",
                        "agency_name": "Agency One",
                        "source_type": "newsletter",
                        "platform": "newsletter",
                        "url": "https://agency.example/newsletter",
                        "archive_status": "manual_seed",
                        "feasibility": "medium",
                        "origin": "manual.registration",
                        "created_at": "2026-06-25T00:00:00+00:00",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    _report, manifest = build_report(
        argparse.Namespace(
            registry=registry,
            config=config,
            manifest=manifest_path,
            probe_homepages=False,
            max_agencies=0,
        )
    )

    preserved = [source for source in manifest["sources"] if source["source_id"] == "agency-one-newsletter-manual"]
    assert preserved
    assert preserved[0]["origin"] == "manual.registration"
    assert manifest["summary"]["archive_status_counts"]["manual_seed"] == 1


def test_discovery_scores_configured_account_terms(tmp_path):
    registry = tmp_path / "registry.json"
    config = tmp_path / "config.json"
    registry.write_text(
        json.dumps(
            [
                {
                    "agency_id": "agency-one",
                    "name": "Agency One",
                    "official_website": "https://agency.example",
                    "social_profiles": {
                        "facebook": {
                            "handle": "Official Agency One",
                            "url": "https://facebook.com/OfficialAgencyOne",
                            "status": "active",
                        },
                        "instagram": {
                            "handle": "Agency One Fan Page",
                            "url": "https://instagram.com/agencyonefan",
                            "status": "candidate",
                        },
                    },
                }
            ]
        ),
        encoding="utf-8",
    )
    config.write_text(
        json.dumps(
            {
                "homepage_probe": {"common_paths": ["/"]},
                "heuristics": {
                    "official_account_terms": ["official"],
                    "negative_account_terms": ["fan", "unofficial"],
                },
                "platform_archive_policy": {
                    "facebook": {"archive_status": "candidate"},
                    "instagram": {"archive_status": "candidate"},
                    "website_page": {"archive_status": "ready"},
                },
            }
        ),
        encoding="utf-8",
    )

    report, _manifest = build_report(
        argparse.Namespace(registry=registry, config=config, probe_homepages=False, max_agencies=0)
    )

    by_platform = {candidate["platform"]: candidate for candidate in report["candidates"] if candidate["source_type"] == "social_profile"}
    assert "official_term:official" in by_platform["facebook"]["trust_signals"]
    assert "negative_term:fan" in by_platform["instagram"]["trust_signals"]
    assert by_platform["facebook"]["confidence_score"] > by_platform["instagram"]["confidence_score"]


def test_discovery_recognizes_medium_and_substack_social_profiles(tmp_path):
    registry = tmp_path / "registry.json"
    config = tmp_path / "config.json"
    registry.write_text(
        json.dumps(
            [
                {
                    "agency_id": "agency-one",
                    "name": "Agency One",
                    "official_website": "https://agency.example",
                    "social_profiles": {
                        "medium": {
                            "handle": "agency-one",
                            "url": "https://medium.com/@agency-one",
                            "status": "active",
                        },
                        "substack": {
                            "handle": "agency-one",
                            "url": "https://agencyone.substack.com",
                            "status": "active",
                        },
                    },
                }
            ]
        ),
        encoding="utf-8",
    )
    config.write_text(
        json.dumps(
            {
                "homepage_probe": {"common_paths": ["/"]},
                "platform_archive_policy": {
                    "medium": {
                        "feasibility": "medium",
                        "archive_status": "candidate",
                        "access_method": "public_html_or_rss",
                        "auth": "none",
                    },
                    "substack": {
                        "feasibility": "medium",
                        "archive_status": "candidate",
                        "access_method": "public_html_or_rss",
                        "auth": "none",
                    },
                    "website_page": {
                        "feasibility": "high",
                        "archive_status": "ready",
                        "access_method": "bounded_public_html",
                        "auth": "none",
                    },
                },
                "heuristics": {
                    "platform_search_templates": [
                        {"platform": "medium", "query": "site:medium.com {agency_name} {domain}"},
                        {"platform": "substack", "query": "site:substack.com {agency_name} {domain}"},
                    ]
                },
            }
        ),
        encoding="utf-8",
    )

    report, _manifest = build_report(
        argparse.Namespace(registry=registry, config=config, probe_homepages=False, max_agencies=0)
    )

    by_platform = {candidate["platform"]: candidate for candidate in report["candidates"] if candidate["source_type"] == "social_profile"}
    assert by_platform["medium"]["source_type"] == "social_profile"
    assert by_platform["substack"]["source_type"] == "social_profile"
    assert any(item["platform"] == "medium" for item in report["platform_search_queries"][0]["queries"])
    assert any(item["platform"] == "substack" for item in report["platform_search_queries"][0]["queries"])


def test_discovery_detects_medium_and_substack_hosts() -> None:
    from scripts.discover_govt_source_candidates import detect_platform, looks_like_feed_url

    assert detect_platform("https://medium.com/@agency-one") == "medium"
    assert detect_platform("https://agencyone.substack.com") == "substack"
    assert looks_like_feed_url("https://agencyone.substack.com/feed")
    assert looks_like_feed_url("https://medium.com/feed/agency-one")


def test_discovery_scores_feedback_learning_file(tmp_path):
    registry = tmp_path / "registry.json"
    config = tmp_path / "config.json"
    learning = tmp_path / "learning.json"
    url = "https://threads.net/@agencyone"
    registry.write_text(
        json.dumps(
            [
                {
                    "agency_id": "agency-one",
                    "name": "Agency One",
                    "official_website": "https://agency.example",
                    "social_profiles": {
                        "threads": {"handle": "agencyone", "url": url, "status": "active"}
                    },
                }
            ]
        ),
        encoding="utf-8",
    )
    learning.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "candidate_id": "old",
                        "agency_id": "agency-one",
                        "platform": "threads",
                        "url": url,
                        "decision": "rejected",
                        "reason": "not the official agency account",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    config.write_text(
        json.dumps(
            {
                "homepage_probe": {"common_paths": ["/"]},
                "heuristics": {"learning_file": str(learning)},
                "platform_archive_policy": {
                    "threads": {"archive_status": "candidate"},
                    "website_page": {"archive_status": "ready"},
                },
            }
        ),
        encoding="utf-8",
    )

    report, _manifest = build_report(
        argparse.Namespace(registry=registry, config=config, probe_homepages=False, max_agencies=0)
    )

    threads = [candidate for candidate in report["candidates"] if candidate["platform"] == "threads"]
    assert len(threads) == 1
    assert "learning_negative" in threads[0]["trust_signals"]
    assert threads[0]["confidence_score"] < 0.5


def test_discovery_emits_medium_and_substack_rss_feeds(tmp_path):
    registry = tmp_path / "registry.json"
    config = tmp_path / "config.json"
    registry.write_text(
        json.dumps(
            [
                {
                    "agency_id": "agency-one",
                    "name": "Agency One",
                    "official_website": "https://agency.example",
                    "social_profiles": {
                        "medium": {
                            "handle": "Agency One",
                            "url": "https://agencyone.medium.com",
                            "status": "active",
                        },
                        "substack": {
                            "handle": "Agency One",
                            "url": "https://agencyone.substack.com",
                            "status": "active",
                        },
                    },
                }
            ]
        ),
        encoding="utf-8",
    )
    config.write_text(
        json.dumps(
            {
                "homepage_probe": {"common_paths": ["/"]},
                "platform_archive_policy": {
                    "medium": {"archive_status": "candidate"},
                    "substack": {"archive_status": "candidate"},
                    "rss": {"archive_status": "ready"},
                    "website_page": {"archive_status": "ready"},
                },
            }
        ),
        encoding="utf-8",
    )

    report, _manifest = build_report(
        argparse.Namespace(registry=registry, config=config, probe_homepages=False, max_agencies=0)
    )

    rss_candidates = [candidate for candidate in report["candidates"] if candidate["source_type"] == "rss_feed"]
    rss_urls = {candidate["url"] for candidate in rss_candidates}

    assert "https://agencyone.medium.com/feed" in rss_urls
    assert "https://agencyone.substack.com/feed" in rss_urls
    assert any(candidate["platform"] == "medium" for candidate in report["candidates"] if candidate["source_type"] == "social_profile")
    assert any(candidate["platform"] == "substack" for candidate in report["candidates"] if candidate["source_type"] == "social_profile")
