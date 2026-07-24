from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from src.bluesky_mirror_programme import ATPROTO_DID_PATTERN, handle_candidates, slugify

DEFAULT_ABBREVIATION_REGISTRY = Path("config/bluesky_mirror_abbreviations.json")
DEFAULT_MIRROR_REGISTRY = Path("config/mirror_accounts.json")
DEFAULT_STALE_LINK_REPORT = Path("conductor/bluesky_mirror_stale_handle_report.json")
SCANNABLE_SUFFIXES = {".json", ".jsonl", ".md", ".py", ".yaml", ".yml"}
EXCLUDED_PARTS = {
    ".git",
    ".playwright-cli",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "historical_archive_normalized",
    "historical_archive_raw",
}
HISTORICAL_EVIDENCE_PATHS = {"conductor/bluesky_mirror_handle_history.jsonl"}
MIGRATION_DOCUMENTATION_PATHS = {"docs/bluesky-agency-mirror-runbook.md"}
GENERATED_REPORT_PATHS = {"conductor/bluesky_mirror_stale_handle_report.json"}
POLICY_CONFIG_PATHS = {"config/bluesky_mirror_abbreviations.json"}


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_abbreviation_registry(registry: Mapping[str, Any]) -> None:
    if registry.get("schema_version") != 1:
        raise ValueError("Abbreviation registry schema_version must be 1.")
    entries = registry.get("entries")
    if not isinstance(entries, list):
        raise ValueError("Abbreviation registry must contain an entries list.")
    seen_agencies: set[str] = set()
    seen_abbreviations: set[tuple[str, str]] = set()
    seen_handles: set[str] = set()
    seen_retired_handles: set[str] = set()
    for entry in entries:
        agency_id = slugify(str(entry.get("agency_id") or ""))
        abbreviation = slugify(str(entry.get("organisation_abbreviation") or ""))
        jurisdiction = slugify(str(entry.get("jurisdiction") or ""))
        handle = str(entry.get("approved_handle") or "")
        account_did = str(entry.get("account_did") or "")
        retired_handles = {
            str(value) for value in (entry.get("retired_handles") or [])
        }
        if not agency_id or agency_id in seen_agencies:
            raise ValueError(f"Missing or duplicate agency_id: {agency_id}")
        key = (abbreviation, jurisdiction)
        if not abbreviation or not jurisdiction or key in seen_abbreviations:
            raise ValueError(f"Missing or duplicate abbreviation/jurisdiction: {key}")
        if handle not in handle_candidates(
            agency_id, abbreviation=abbreviation, jurisdiction=jurisdiction
        ):
            raise ValueError(f"Approved handle does not match policy for {agency_id}: {handle}")
        if handle in seen_handles:
            raise ValueError(f"Duplicate approved handle: {handle}")
        if handle in retired_handles:
            raise ValueError(f"Approved handle is also retired: {handle}")
        duplicate_retired = retired_handles & seen_retired_handles
        if duplicate_retired:
            raise ValueError(f"Duplicate retired handles: {sorted(duplicate_retired)}")
        if account_did and not ATPROTO_DID_PATTERN.fullmatch(account_did):
            raise ValueError(f"Invalid account DID for {agency_id}: {account_did}")
        seen_agencies.add(agency_id)
        seen_abbreviations.add(key)
        seen_handles.add(handle)
        seen_retired_handles.update(retired_handles)


def resolve_handle(handle: str, *, timeout: int = 20) -> str:
    query = urlencode({"handle": handle})
    request = Request(
        f"https://public.api.bsky.app/xrpc/com.atproto.identity.resolveHandle?{query}",
        headers={"Accept": "application/json"},
    )
    with urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return str(payload.get("did") or "")


def verify_handle_identity(handle: str, expected_did: str) -> dict[str, Any]:
    actual_did = resolve_handle(handle)
    return {
        "handle": handle,
        "expected_did": expected_did,
        "actual_did": actual_did,
        "valid": bool(actual_did and actual_did == expected_did),
        "verified_at": datetime.now(UTC).isoformat(),
    }


def migration_plan(
    mirror: Mapping[str, Any],
    abbreviation_entry: Mapping[str, Any],
    *,
    old_handle: str,
) -> dict[str, Any]:
    return {
        "mirror_id": mirror["mirror_id"],
        "account_did": abbreviation_entry["account_did"],
        "old_handle": old_handle,
        "new_handle": abbreviation_entry["approved_handle"],
        "environment": mirror["environment"],
        "steps": [
            "verify_old_handle_did",
            "verify_new_handle_availability",
            "update_atproto_handle",
            "verify_new_handle_did",
            "update_registry",
            "update_github_environment_handle",
            "run_non_posting_preflight",
            "record_handle_history",
            "scan_stale_links",
        ],
    }


def find_stale_handle_references(
    root: str | Path, old_handles: list[str]
) -> list[dict[str, Any]]:
    base = Path(root)
    matches: list[dict[str, Any]] = []
    for path in sorted(base.rglob("*")):
        if not path.is_file() or path.suffix.casefold() not in SCANNABLE_SUFFIXES:
            continue
        if any(part in EXCLUDED_PARTS for part in path.parts):
            continue
        relative_path = path.relative_to(base).as_posix()
        if relative_path in GENERATED_REPORT_PATHS:
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(lines, start=1):
            for handle in old_handles:
                if handle in line:
                    classification = "actionable_stale_reference"
                    actionable = True
                    if relative_path in HISTORICAL_EVIDENCE_PATHS:
                        classification = "historical_evidence"
                        actionable = False
                    elif relative_path in MIGRATION_DOCUMENTATION_PATHS:
                        classification = "migration_documentation"
                        actionable = False
                    elif relative_path in POLICY_CONFIG_PATHS:
                        classification = "retired_handle_policy"
                        actionable = False
                    elif relative_path.startswith("tests/"):
                        classification = "test_fixture"
                        actionable = False
                    matches.append(
                        {
                            "path": relative_path,
                            "line": line_number,
                            "handle": handle,
                            "classification": classification,
                            "actionable": actionable,
                        }
                    )
    return matches


def stale_link_report(root: str | Path, old_handles: list[str]) -> dict[str, Any]:
    matches = find_stale_handle_references(root, old_handles)
    actionable = [row for row in matches if row["actionable"]]
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "old_handles": sorted(set(old_handles)),
        "match_count": len(matches),
        "actionable_count": len(actionable),
        "matches": matches,
    }
