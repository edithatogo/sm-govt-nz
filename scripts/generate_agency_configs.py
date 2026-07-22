#!/usr/bin/env python3
"""Generate per-agency source inventory and RSS feed config files from discovery data."""

import json
import sys
import io
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
MANIFEST_PATH = ROOT / "conductor" / "govt_archive_source_manifest.json"
RSS_LIVE_PATH = ROOT / "conductor" / "govt_archive_registered_sources_rss_live.json"

DATASET_OUTPUTS = {
    "hugging_face": {
        "enabled": True,
        "secret_requirements": ["HF_TOKEN", "HF_DATASET_REPO_ID"],
        "artifacts": ["normalized_jsonl", "normalized_parquet", "manifest", "dataset_card"],
    },
    "zenodo": {
        "enabled": True,
        "secret_requirements": ["ZENODO_TOKEN", "ZENODO_DEPOSIT_ENDPOINT"],
        "artifacts": ["release_snapshot", "manifest", "checksums", "citation_metadata"],
    },
}

PHASE_REVIEW = {"commit_after_each_task": True, "review_after_each_phase": True,
    "review_after_track": True, "future_syndication_tracks": "one_platform_account_per_track"}


def load_json(path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def bluesky_contract(aid, name, handle, url):
    return {"id": aid + "-bluesky", "source_platform": "bluesky",
        "source_kind": "social_feed", "display_name": name + " Bluesky",
        "account": handle, "url": url or ("https://bsky.app/profile/" + handle),
        "access_method": "public_at_protocol", "auth": "none", "status": "healthy",
        "dedupe_keys": ["at_uri", "canonical_url", "content_hash"],
        "raw_path_template": "historical_archive_raw/bluesky/{yyyy_mm}/{record_id}.json",
        "normalized_path_template": "historical_archive_normalized/bluesky/{yyyy_mm}.jsonl",
        "rate_limit_policy": "Use bounded page sizes and persist cursors.",
        "archive_only_guarantee": "Backfills must not advance outbound syndication state.",
        "failure_modes": ["rate_limited", "network_error", "schema_changed"]}


def bluesky_handle_from_source_url(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower().removeprefix("www.")
    if host != "bsky.app" and not host.endswith(".bsky.app"):
        return ""
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) >= 2 and parts[0] == "profile":
        return parts[1]
    return ""

def rss_contract(aid, name, website, seed_pages):
    acct = website.replace("https://", "").replace("http://", "").rstrip("/") if website else aid
    return {"id": aid + "-rss-website", "source_platform": "rss",
        "source_kind": "rss_website", "display_name": name + " RSS & Website",
        "account": acct, "url": website or (seed_pages[0] if seed_pages else ""),
        "access_method": "public_rss", "auth": "none", "status": "healthy",
        "seed_pages": seed_pages,
        "dedupe_keys": ["feed_entry_id", "canonical_url", "content_hash"],
        "raw_path_template": "historical_archive_raw/rss/{yyyy_mm}/{record_id}.json",
        "normalized_path_template": "historical_archive_normalized/rss/{yyyy_mm}.jsonl",
        "rate_limit_policy": "Use feedparser for feeds and bounded HTML fetches.",
        "archive_only_guarantee": "RSS records must not alter outbound syndication cursors.",
        "failure_modes": ["feed_unavailable", "network_error", "html_changed"]}


def website_contract(aid, name, website, urls):
    acct = website.replace("https://", "").replace("http://", "").rstrip("/") if website else aid
    return {"id": aid + "-website-pages", "source_platform": acct,
        "source_kind": "website_page", "display_name": name + " Website Pages",
        "account": acct, "url": website or (urls[0] if urls else ""),
        "access_method": "public_html_from_rss_links", "auth": "none", "status": "healthy",
        "seed_pages": urls,
        "dedupe_keys": ["canonical_url", "content_hash"],
        "raw_path_template": "historical_archive_raw/website/{yyyy_mm}/{record_id}.json",
        "normalized_path_template": "historical_archive_normalized/website/{yyyy_mm}.jsonl",
        "rate_limit_policy": "Fetch only bounded public pages linked from archived feed records.",
        "archive_only_guarantee": "Website records must not alter outbound syndication cursors.",
        "failure_modes": ["network_error", "html_changed", "unavailable"]}


def load_registry():
    result = {}
    for p in [ROOT / "registry" / "government_directory.json", ROOT / "registry" / "agencies.json"]:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            agencies = data if isinstance(data, list) else data.get("agencies", [])
            for a in agencies:
                result[a["agency_id"]] = a
        except (FileNotFoundError, json.JSONDecodeError):
            continue
    return result


def write_newline(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + chr(10), encoding="utf-8")


def write_jsonl(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + chr(10), encoding="utf-8")


def write_agency_config(aid, agency_sources, rss_by_agency, registry_by_id, config_dir, generated_at):
    reg = registry_by_id.get(aid, {})
    name = reg.get("name", aid) or aid
    website = reg.get("official_website", "") or ""
    sources = agency_sources.get(aid, [])
    config_path = config_dir / (aid + "_sources.json")
    existing_contracts_by_id = {}
    if config_path.exists():
        try:
            existing_contracts_by_id = {
                c.get("id"): c
                for c in load_json(config_path).get("contracts", [])
                if c.get("id")
            }
        except (OSError, json.JSONDecodeError):
            existing_contracts_by_id = {}

    contracts = []
    for contract_id, contract in existing_contracts_by_id.items():
        contracts.append(contract)

    for s in sources:
        if s.get("platform") == "bluesky" and s.get("archive_status") == "ready":
            acct = s.get("account", "") or bluesky_handle_from_source_url(s.get("url", ""))
            if not acct:
                continue
            if aid + "-bluesky" not in existing_contracts_by_id:
                contracts.append(bluesky_contract(aid, name, acct, s.get("url", "")))

    rss_feeds = rss_by_agency.get(aid, set())
    existing_feeds = []
    existing_seed_pages = []
    rss_path = config_dir / (aid + "_rss_feeds.json")
    if rss_path.exists():
        try:
            existing_rss = load_json(rss_path)
            existing_feeds = existing_rss.get("feeds", [])
            existing_seed_pages = existing_rss.get("seed_pages", [])
            rss_feeds.update(f.get("feed_url") for f in existing_feeds if f.get("feed_url"))
        except (OSError, json.JSONDecodeError):
            existing_feeds = []
            existing_seed_pages = []

    has_rss = False
    if rss_feeds:
        if aid + "-rss-website" not in existing_contracts_by_id:
            contracts.append(rss_contract(aid, name, website, sorted(rss_feeds)))
        has_rss = True
        existing_feed_urls = {f.get("feed_url") for f in existing_feeds}
        new_feeds = [{"discovery_method": "manifest.archive_registered_sources",
                "feed_type": "application/rss+xml", "feed_url": url, "seed_page": url,
                "title": "RSS Feed"} for url in sorted(rss_feeds) if url not in existing_feed_urls]
        all_feeds = sorted(existing_feeds + new_feeds, key=lambda item: item.get("feed_url", ""))
        existing_seed_urls = {p.get("seed_page") for p in existing_seed_pages}
        new_seed_pages = [{"error": "", "feed_count": 1, "seed_page": url,
                "status": "healthy"} for url in sorted(rss_feeds) if url not in existing_seed_urls]
        all_seed_pages = sorted(existing_seed_pages + new_seed_pages, key=lambda item: item.get("seed_page", ""))
        rss_config = {"agency_id": aid, "feed_count": len(all_feeds),
            "feeds": all_feeds, "generated_at": generated_at,
            "seed_page_count": len(all_seed_pages), "seed_pages": all_seed_pages}
        write_newline(config_dir / (aid + "_rss_feeds.json"), rss_config)

    wp_urls = [s.get("url", "") for s in sources
        if s.get("platform") == "website_page" and s.get("url")]
    if wp_urls and website and not has_rss:
        if aid + "-website-pages" not in existing_contracts_by_id:
            contracts.append(website_contract(aid, name, website, wp_urls))

    if not contracts:
        return False

    inventory = {"agency_id": aid, "agency_name": name, "archive_only": True,
        "contracts": contracts, "dataset_outputs": DATASET_OUTPUTS,
        "phase_review_contract": PHASE_REVIEW, "generated_at": generated_at}
    write_jsonl(config_dir / (aid + "_sources.json"), inventory)
    print("  Wrote: " + aid + "_sources.json")
    return True


def main():
    config_dir = CONFIG_DIR
    config_dir.mkdir(parents=True, exist_ok=True)

    manifest = load_json(MANIFEST_PATH)
    rss_live = load_json(RSS_LIVE_PATH)
    registry_by_id = load_registry()

    agency_sources = {}
    for s in manifest["sources"]:
        aid = s["agency_id"]
        agency_sources.setdefault(aid, []).append(s)

    rss_by_agency = {}
    for x in rss_live["results"]:
        if x["status"] == "captured":
            aid = x["agency_id"]
            rss_by_agency.setdefault(aid, set()).add(x["url"])

    generated_at = datetime.now(timezone.utc).isoformat()
    processed = set()

    for aid in sorted(rss_by_agency.keys()):
        if write_agency_config(aid, agency_sources, rss_by_agency, registry_by_id, config_dir, generated_at):
            processed.add(aid)

    for s in manifest["sources"]:
        if s.get("platform") == "bluesky" and s.get("archive_status") == "ready":
            aid = s["agency_id"]
            if aid not in processed:
                if write_agency_config(aid, agency_sources, rss_by_agency, registry_by_id, config_dir, generated_at):
                    processed.add(aid)

    existing_index = {}
    index_path = config_dir / "agencies_index.json"
    if index_path.exists():
        try:
            existing_index = {
                item.get("agency_id"): item
                for item in load_json(index_path).get("agencies", [])
                if item.get("agency_id")
            }
        except (OSError, json.JSONDecodeError):
            existing_index = {}

    agencies_index = []
    for aid in sorted(processed):
        data = load_json(config_dir / (aid + "_sources.json"))
        contracts = data.get("contracts", [])
        source_kinds = sorted({c.get("source_kind") for c in contracts if c.get("source_kind")})
        platforms = sorted({c.get("source_platform") for c in contracts if c.get("source_platform")})
        rss_config_file = aid + "_rss_feeds.json" if "rss" in platforms else None
        agencies_index.append({
            "agency_id": aid,
            "agency_name": data.get("agency_name"),
            "archival_cadence": "every-6h" if "social_feed" in source_kinds else "daily",
            "capture_priority": "high",
            "config_file": aid + "_sources.json",
            "contract_count": len(contracts),
            "platforms": platforms,
            "rss_config_file": rss_config_file,
            "source_types": source_kinds,
            "workflow_pattern": source_kinds[0] + "-only" if len(source_kinds) == 1 else "multi-source",
        })
    for agency_id, item in existing_index.items():
        if agency_id not in {entry["agency_id"] for entry in agencies_index}:
            agencies_index.append(item)
    agencies_index.sort(key=lambda item: item["agency_id"])
    write_newline(config_dir / "agencies_index.json", {
        "agencies": agencies_index,
        "generated_at": generated_at,
        "total": len(agencies_index),
    })

    print()
    print("Generated configs for " + str(len(processed)) + " agencies:")
    for aid in sorted(processed):
        print("  " + aid)

if __name__ == "__main__":
    main()

