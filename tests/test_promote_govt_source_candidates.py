import argparse
import json
from pathlib import Path

from scripts.promote_govt_source_candidates import register_selected_candidates, select_candidates


def test_promote_govt_source_candidates_registers_ready_feed_and_page_sources(tmp_path: Path) -> None:
    report_path = tmp_path / "report.json"
    manifest_path = tmp_path / "manifest.json"
    report_path.write_text(
        json.dumps(
            {
                "candidates": [
                    {
                        "candidate_id": "rss-1",
                        "agency_id": "agency-rss",
                        "agency_name": "Agency RSS",
                        "source_type": "rss_feed",
                        "platform": "rss",
                        "url": "https://example.govt.nz/feed",
                        "account": "https://example.govt.nz",
                        "feasibility": "high",
                        "archive_status": "ready",
                        "access_method": "public_rss",
                        "auth": "none",
                        "origin": "homepage.link",
                        "confidence_score": 0.6,
                        "status": "discovered",
                        "trust_signals": ["trusted_domain_suffix"],
                    },
                    {
                        "candidate_id": "api-1",
                        "agency_id": "agency-api",
                        "agency_name": "Agency API",
                        "source_type": "api_endpoint",
                        "platform": "api",
                        "url": "https://api.example.govt.nz/openapi.json",
                        "account": "https://example.govt.nz",
                        "feasibility": "medium",
                        "archive_status": "ready",
                        "access_method": "public_api_or_openapi",
                        "auth": "none",
                        "origin": "homepage.link",
                        "confidence_score": 0.7,
                        "status": "discovered",
                        "trust_signals": ["trusted_domain_suffix"],
                    },
                    {
                        "candidate_id": "newsletter-1",
                        "agency_id": "agency-news",
                        "agency_name": "Agency News",
                        "source_type": "newsletter",
                        "platform": "newsletter",
                        "url": "https://example.govt.nz/newsletter",
                        "archive_status": "candidate",
                        "confidence_score": 0.95,
                        "status": "discovered",
                    },
                    {
                        "candidate_id": "page-1",
                        "agency_id": "agency-page",
                        "agency_name": "Agency Page",
                        "source_type": "website_page",
                        "platform": "website_page",
                        "url": "https://example.govt.nz/news",
                        "account": "https://example.govt.nz",
                        "feasibility": "high",
                        "archive_status": "ready",
                        "access_method": "bounded_public_html",
                        "auth": "none",
                        "origin": "homepage.link",
                        "confidence_score": 0.9,
                        "status": "active",
                        "trust_signals": ["registry_known"],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    manifest_path.write_text(json.dumps({"sources": []}), encoding="utf-8")

    report = json.loads(report_path.read_text(encoding="utf-8"))
    selected = select_candidates(report, {"rss_feed", "api_endpoint", "website_page"}, 0.6)
    assert [item["candidate_id"] for item in selected] == ["page-1", "api-1", "rss-1"]

    result = register_selected_candidates(report, manifest_path, {"rss_feed", "api_endpoint", "website_page"}, 0.6)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert result["selected_count"] == 3
    assert result["added_count"] == 3
    assert result["updated_count"] == 0
    assert manifest["summary"]["total_sources"] == 3
    assert manifest["summary"]["archive_status_counts"] == {"ready": 3}
    by_id = {source["source_id"]: source for source in manifest["sources"]}
    assert by_id["rss-1"]["platform"] == "rss"
    assert by_id["api-1"]["source_type"] == "api_endpoint"
    assert by_id["page-1"]["archive_status"] == "ready"
    assert "Promoted from discovery" in by_id["rss-1"]["notes"]


def test_govt_source_discovery_workflow_promotes_ready_candidates() -> None:
    workflow = Path(".github/workflows/govt_source_discovery.yml").read_text(encoding="utf-8")

    assert "scripts/promote_govt_source_candidates.py" in workflow
    assert "Promote ready source candidates" in workflow
