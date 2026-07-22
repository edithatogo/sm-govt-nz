from __future__ import annotations

import json

from scripts.generate_agency_configs import write_agency_config


def test_bluesky_without_account_is_not_generated(tmp_path) -> None:
    processed = write_agency_config(
        "agency",
        {"agency": [{"platform": "bluesky", "archive_status": "ready", "url": ""}]},
        {},
        {"agency": {"name": "Agency", "official_website": "https://agency.govt.nz"}},
        tmp_path,
        "2026-07-22T00:00:00+00:00",
    )

    assert processed is False
    assert not (tmp_path / "agency_sources.json").exists()


def test_existing_manual_contract_and_feed_are_preserved(tmp_path) -> None:
    (tmp_path / "agency_sources.json").write_text(
        json.dumps({"contracts": [{"id": "agency-manual", "source_kind": "newsletter"}]}),
        encoding="utf-8",
    )
    (tmp_path / "agency_rss_feeds.json").write_text(
        json.dumps({"feeds": [{"feed_url": "https://agency.govt.nz/manual.xml"}], "seed_pages": []}),
        encoding="utf-8",
    )

    assert write_agency_config(
        "agency",
        {"agency": [{"platform": "bluesky", "archive_status": "ready", "account": "agency.bsky.social"}]},
        {"agency": {"https://agency.govt.nz/discovered.xml"}},
        {"agency": {"name": "Agency", "official_website": "https://agency.govt.nz"}},
        tmp_path,
        "2026-07-22T00:00:00+00:00",
    )

    config = json.loads((tmp_path / "agency_sources.json").read_text(encoding="utf-8"))
    feeds = json.loads((tmp_path / "agency_rss_feeds.json").read_text(encoding="utf-8"))
    assert {c["id"] for c in config["contracts"]} == {"agency-manual", "agency-bluesky", "agency-rss-website"}
    assert {f["feed_url"] for f in feeds["feeds"]} == {
        "https://agency.govt.nz/manual.xml",
        "https://agency.govt.nz/discovered.xml",
    }
