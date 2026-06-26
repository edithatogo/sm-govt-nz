#!/usr/bin/env python3
"""Validate all per-agency config files for correct JSON schema and required fields.

Checks:
- Valid JSON
- Required top-level keys present (_sources.json and _rss_feeds.json)
- Contract structure matches expected schema
- Agency IDs consistent between _sources.json and _rss_feeds.json
- courts-of-nz config has proper contracts (bluesky + RSS)
- Reports any missing configs or anomalies
"""

import json
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"

SOURCES_REQUIRED_KEYS = [
    "agency_id", "agency_name", "archive_only", "contracts",
    "dataset_outputs", "generated_at", "phase_review_contract"
]

CONTRACT_REQUIRED_KEYS = [
    "id", "source_platform", "source_kind", "display_name",
    "account", "url", "access_method", "auth", "status",
    "dedupe_keys", "raw_path_template", "normalized_path_template",
    "rate_limit_policy", "archive_only_guarantee", "failure_modes"
]

RSS_FEEDS_REQUIRED_KEYS = [
    "agency_id", "feed_count", "feeds", "generated_at",
    "seed_page_count", "seed_pages"
]


def validate_sources_config(data, path):
    """Validate a _sources.json config file."""
    errors = []
    for key in SOURCES_REQUIRED_KEYS:
        if key not in data:
            errors.append(f"  MISSING key: {key}")
    contracts = data.get("contracts", [])
    if not contracts:
        errors.append("  No contracts defined (min 1 required)")
    for idx, contract in enumerate(contracts):
        for key in CONTRACT_REQUIRED_KEYS:
            if key not in contract:
                errors.append(f"  Contract[{idx}] MISSING key: {key}")
        if contract.get("source_platform") == "bluesky":
            acct = contract.get("account", "")
            if not acct:
                errors.append(f"  Contract[{idx}] Bluesky account is empty")
        # Only check raw_path_template for standard platforms (bluesky, rss, email, x)
        # Website contracts use domain name as source_platform, not 'website'
        std_platform = contract.get("source_platform", "")
        raw_tpl = contract.get("raw_path_template", "")
        if std_platform in ("bluesky", "rss", "email", "x") and raw_tpl:
            if std_platform not in raw_tpl:
                errors.append(
                    f"  Contract[{idx}] raw_path_template '{raw_tpl}' "
                    f"doesn't match platform '{std_platform}'")
    dout = data.get("dataset_outputs", {})
    for ds_name in ["hugging_face", "zenodo"]:
        ds = dout.get(ds_name, {})
        if not ds.get("enabled"):
            errors.append(f"  dataset_outputs.{ds_name}.enabled is not True")
    return errors

def validate_rss_feeds_config(data, path):
    """Validate a _rss_feeds.json config file."""
    errors = []
    for key in RSS_FEEDS_REQUIRED_KEYS:
        if key not in data:
            errors.append(f"  MISSING key: {key}")
    feed_count = data.get("feed_count", -1)
    feeds = data.get("feeds", [])
    if feed_count != len(feeds):
        errors.append(f"  feed_count ({feed_count}) != len(feeds) ({len(feeds)})")
    spr_count = data.get("seed_page_count", -1)
    spr = data.get("seed_pages", [])
    if spr_count != len(spr):
        errors.append(
            f"  seed_page_count ({spr_count}) != len(seed_pages) ({len(spr)})")
    for idx, feed in enumerate(feeds):
        if "feed_url" not in feed:
            errors.append(f"  feeds[{idx}] missing feed_url")
        if "feed_type" not in feed:
            errors.append(f"  feeds[{idx}] missing feed_type")
    return errors


def main():
    print("=" * 60)
    print("Agency Config Validation Report")
    print("=" * 60)
    print()
    sources_files = sorted(CONFIG_DIR.glob("*_sources.json"))
    rss_files = sorted(CONFIG_DIR.glob("*_rss_feeds.json"))
    print(f"Found {len(sources_files)} _sources.json files")
    print(f"Found {len(rss_files)} _rss_feeds.json files")
    print()
    all_pass = True
    total_errors = 0
    agency_ids_sources = set()
    agency_ids_rss = set()

    print("--- Validating _sources.json files ---")
    for sp in sources_files:
        fname = sp.name
        try:
            data = json.loads(sp.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"  INVALID JSON: {fname} - {e}")
            all_pass = False
            total_errors += 1
            continue
        aid = data.get("agency_id", "unknown")
        agency_ids_sources.add(aid)
        print(f"  {fname} (agency: {aid})")
        errors = validate_sources_config(data, sp)
        if errors:
            all_pass = False
            total_errors += len(errors)
            for err in errors:
                print(f"    {err}")
    print()

    print("--- Validating _rss_feeds.json files ---")
    for rp in rss_files:
        fname = rp.name
        try:
            data = json.loads(rp.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"  INVALID JSON: {fname} - {e}")
            all_pass = False
            total_errors += 1
            continue
        aid = data.get("agency_id", "unknown")
        agency_ids_rss.add(aid)
        print(f"  {fname} (agency: {aid})")
        errors = validate_rss_feeds_config(data, rp)
        if errors:
            all_pass = False
            total_errors += len(errors)
            for err in errors:
                print(f"    {err}")
    print()

    print("--- Cross-checking agency IDs ---")
    for sp in sources_files:
        try:
            data = json.loads(sp.read_text(encoding="utf-8"))
            aid = data.get("agency_id", "")
        except (json.JSONDecodeError, IOError):
            continue
        companion = CONFIG_DIR / f"{aid}_rss_feeds.json"
        if companion.exists():
            try:
                rss_data = json.loads(companion.read_text(encoding="utf-8"))
                rss_aid = rss_data.get("agency_id", "")
                if rss_aid != aid:
                    print(f"  MISMATCH: {aid} (sources) vs {rss_aid} (rss_feeds)")
                    all_pass = False
                    total_errors += 1
            except (json.JSONDecodeError, IOError):
                pass
    print()

    print("--- Special checks: courts-of-nz ---")
    courts_path = CONFIG_DIR / "courts-of-nz_sources.json"
    if courts_path.exists():
        try:
            data = json.loads(courts_path.read_text(encoding="utf-8"))
            contracts = data.get("contracts", [])
            plat_names = {c.get("source_platform"): c for c in contracts}
            if "bluesky" not in plat_names:
                print(f"  WARNING: courts-of-nz missing Bluesky contract")
                total_errors += 1
            if "rss" not in plat_names:
                print(f"  WARNING: courts-of-nz missing RSS contract")
                total_errors += 1
            if "bluesky" in plat_names and "rss" in plat_names:
                print(
                    f"  OK: courts-of-nz has Bluesky + RSS contracts "
                    f"({len(contracts)} total)")
            rss_comp = CONFIG_DIR / "courts-of-nz_rss_feeds.json"
            if rss_comp.exists():
                rss_data = json.loads(rss_comp.read_text(encoding="utf-8"))
                print(f"  RSS feeds present: "
                      f"{rss_data.get('feed_count', 0)} feed(s)")
                for feed in rss_data.get("feeds", []):
                    fu = feed.get("feed_url", "")
                    print(f"    Feed URL: {fu}")
            else:
                print(f"  WARNING: courts-of-nz_rss_feeds.json missing")
                total_errors += 1
        except (json.JSONDecodeError, IOError) as e:
            print(f"  ERROR reading courts-of-nz config: {e}")
            total_errors += 1
    else:
        print(f"  WARNING: courts-of-nz_sources.json not found")
        total_errors += 1
    print()

    print("=" * 60)
    if all_pass:
        print("RESULT: ALL CONFIGS VALID")
    else:
        print(f"RESULT: {total_errors} ISSUE(S) FOUND")
    print(f"       {len(sources_files)} sources files")
    print(f"       {len(rss_files)} rss_feeds files")
    print(f"       {len(agency_ids_sources)} unique agency IDs in sources")
    print(f"       {len(agency_ids_rss)} unique agency IDs in rss_feeds")
    print("=" * 60)
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())

