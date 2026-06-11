import json

from scripts.gap_analyzer import analyze_registry, load_registry, write_report


def test_analyze_registry_calculates_platform_coverage_and_gaps() -> None:
    agencies = [
        {
            "agency_id": "open-agency",
            "name": "Open Agency",
            "type": "Ministry",
            "portfolio": "Test",
            "social_profiles": {
                "bluesky": {"status": "active"},
                "linkedin": {"status": "active"},
                "x": {"status": "deactivated", "deactivated_at": "2026-01"},
            },
        },
        {
            "agency_id": "closed-agency",
            "name": "Closed Agency",
            "type": "Crown Entity",
            "portfolio": "Test",
            "social_profiles": {
                "facebook": {"status": "active"},
                "linkedin": {"status": "active"},
            },
        },
    ]

    report = analyze_registry(agencies)

    assert report["agency_count"] == 2
    assert report["platform_coverage"]["bluesky"] == 1
    assert report["platform_coverage"]["linkedin"] == 2
    assert report["open_network_coverage"] == 1
    assert report["proprietary_network_coverage"] == 2
    assert report["proprietary_without_open"][0]["agency_id"] == "closed-agency"
    assert report["deactivated_profiles"][0]["platform"] == "x"


def test_write_and_load_report_inputs(tmp_path) -> None:
    registry_path = tmp_path / "agencies.json"
    output_path = tmp_path / "gap_analysis.json"
    registry_path.write_text(
        json.dumps(
            [
                {
                    "agency_id": "rss-agency",
                    "name": "RSS Agency",
                    "type": "Department",
                    "portfolio": "Test",
                    "social_profiles": {"rss": {"status": "active"}},
                }
            ]
        ),
        encoding="utf-8",
    )

    report = analyze_registry(load_registry(registry_path))
    write_report(report, output_path)

    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert saved["open_network_coverage"] == 1
    assert saved["platform_coverage"]["rss"] == 1