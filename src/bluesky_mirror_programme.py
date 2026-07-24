from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from src.bluesky import BlueskyApiClient, BlueskyPost
from src.syndication import SyndicationResult

REGISTRY_PATH = Path("config/mirror_accounts.json")
STATE_PATH = Path("conductor/bluesky_mirror_runtime_state.json")
AUDIT_PATH = Path("conductor/bluesky_mirror_post_audit.jsonl")
DEAD_LETTER_PATH = Path("conductor/bluesky_mirror_dead_letter.jsonl")
STATE_DIR = Path("conductor/bluesky_mirror_state")
AUDIT_DIR = Path("conductor/bluesky_mirror_audit")
DEAD_LETTER_DIR = Path("conductor/bluesky_mirror_dead_letter")
RECOVERY_REPORT_DIR = Path("conductor/bluesky_mirror_recovery")
REPORT_PATH = Path("conductor/bluesky_mirror_programme_report.json")
ELIGIBILITY_REPORT_DIR = Path("conductor/bluesky_mirror_eligibility")
SOCIAL_PLATFORMS = {
    "activitypub",
    "bluesky",
    "facebook",
    "instagram",
    "linkedin",
    "medium",
    "substack",
    "threads",
    "x",
    "youtube",
}
MIRRORABLE_SOURCE_KINDS = frozenset(
    {"post", "social_post", "social_feed", "status", "feed_item"}
)
TERMINAL_SOURCE_STATES = {"deleted", "private", "withdrawn", "unverifiable"}
SECRET_FIELD_PATTERN = re.compile(r"password|secret|token|cookie|verification", re.I)
JURISDICTIONAL_HANDLE_PATTERN = re.compile(
    r"^[a-z0-9](?:[a-z0-9-]{0,58}[a-z0-9])?-"
    r"[a-z0-9](?:[a-z0-9-]{0,12}[a-z0-9])?-arc(?:-[2-9][0-9]*)?\.bsky\.social$"
)
ATPROTO_DID_PATTERN = re.compile(r"^did:[a-z0-9]+:[A-Za-z0-9._:%-]+$")
BLUESKY_APP_PASSWORD_PATTERN = re.compile(
    r"^[a-z0-9]{4}(?:-[a-z0-9]{4}){3}$",
    re.I,
)
VALID_STATES = {
    "candidate",
    "operator_onboarding",
    "credential_migration_required",
    "preflight_ready",
    "backfilling",
    "live",
    "paused",
    "retired",
}
PUBLICATION_STATE_VERSION = 1
MAX_RECONCILIATION_ATTEMPTS = 12


@dataclass(frozen=True)
class MirrorRecord:
    record_id: str
    agency_id: str
    source_id: str
    source_platform: str
    created_at: str
    content: str
    source_url: str
    public_name: str = ""


@dataclass(frozen=True)
class SourceEligibilityResult:
    eligible: bool
    reason: str
    record_id: str
    source_id: str
    agency_id: str
    source_platform: str
    source_kind: str
    source_url: str


def slugify(value: str, *, maximum: int = 40) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return slug[:maximum].rstrip("-") or "agency"


def handle_candidates(
    agency_id: str,
    *,
    abbreviation: str | None = None,
    jurisdiction: str = "nz",
) -> list[str]:
    organisation = slugify(abbreviation or agency_id, maximum=42)
    jurisdiction_slug = slugify(jurisdiction, maximum=14)
    base = f"{organisation}-{jurisdiction_slug}-arc"
    return [f"{base}.bsky.social", f"{base}-2.bsky.social"]


def load_registry(path: str | Path = REGISTRY_PATH) -> dict[str, Any]:
    registry = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_registry(registry)
    return registry


def validate_registry(registry: Mapping[str, Any]) -> None:
    if registry.get("schema_version") != 2:
        raise ValueError("Mirror registry schema_version must be 2.")
    mirrors = registry.get("mirrors")
    if not isinstance(mirrors, list):
        raise ValueError("Mirror registry must contain a mirrors list.")
    seen_ids: set[str] = set()
    seen_handles: set[str] = set()
    for mirror in mirrors:
        if not isinstance(mirror, Mapping):
            raise ValueError("Every mirror row must be an object.")
        flattened = json.dumps(mirror, sort_keys=True)
        for field in mirror:
            if SECRET_FIELD_PATTERN.search(str(field)):
                raise ValueError(f"Secret-like field is forbidden in mirror registry: {field}")
        if "@gmail.com" in flattened.casefold() or "+bluesky" in flattened.casefold():
            raise ValueError("Complete registration aliases are forbidden in mirror registry.")
        mirror_id = str(mirror.get("mirror_id") or "")
        handle = str(mirror.get("handle") or "")
        state = str(mirror.get("lifecycle_state") or "")
        account_did = str(mirror.get("account_did") or "")
        handle_policy_version = mirror.get("handle_policy_version")
        if not mirror_id or mirror_id in seen_ids:
            raise ValueError(f"Missing or duplicate mirror_id: {mirror_id}")
        if handle and handle in seen_handles:
            raise ValueError(f"Duplicate mirror handle: {handle}")
        if handle_policy_version == 1:
            if not JURISDICTIONAL_HANDLE_PATTERN.fullmatch(handle):
                raise ValueError(f"Mirror {mirror_id} violates jurisdictional handle policy: {handle}")
            if not str(mirror.get("organisation_abbreviation") or ""):
                raise ValueError(f"Mirror {mirror_id} lacks an organisation abbreviation.")
            if not str(mirror.get("jurisdiction") or ""):
                raise ValueError(f"Mirror {mirror_id} lacks a jurisdiction.")
            public_name = str(mirror.get("public_name") or "").strip()
            if not public_name:
                raise ValueError(f"Mirror {mirror_id} lacks a public name.")
            if len(public_name) > 64:
                raise ValueError(f"Mirror {mirror_id} public name exceeds 64 characters.")
        if account_did and not ATPROTO_DID_PATTERN.fullmatch(account_did):
            raise ValueError(f"Mirror {mirror_id} has an invalid AT Protocol DID.")
        if state not in VALID_STATES:
            raise ValueError(f"Invalid lifecycle state for {mirror_id}: {state}")
        if mirror.get("enabled") and state not in {"backfilling", "live"}:
            raise ValueError(f"Enabled mirror {mirror_id} must be backfilling or live.")
        if not str(mirror.get("environment") or "").startswith("bluesky-mirror-"):
            raise ValueError(f"Mirror {mirror_id} lacks an isolated environment.")
        seen_ids.add(mirror_id)
        if handle:
            seen_handles.add(handle)


def build_registry_from_manifest(
    manifest: Mapping[str, Any] | list[Mapping[str, Any]],
    existing: Mapping[str, Any],
) -> dict[str, Any]:
    rows = _manifest_rows(manifest)
    agencies: dict[str, dict[str, Any]] = {}
    for row in rows:
        agency_id = slugify(str(row.get("agency_id") or ""))
        platform = str(row.get("platform") or row.get("source_type") or "").casefold()
        if not agency_id or platform not in SOCIAL_PLATFORMS:
            continue
        group = agencies.setdefault(
            agency_id,
            {
                "agency_name": str(row.get("agency_name") or agency_id),
                "source_ids": set(),
                "source_urls": set(),
                "source_platforms": set(),
            },
        )
        if row.get("source_id"):
            group["source_ids"].add(str(row["source_id"]))
        if row.get("url"):
            group["source_urls"].add(str(row["url"]))
        group["source_platforms"].add(platform)

    current = {str(row.get("agency_id")): dict(row) for row in existing.get("mirrors", [])}
    mirrors: list[dict[str, Any]] = []
    for agency_id, group in sorted(agencies.items()):
        row = current.get(agency_id, {})
        public_name = str(row.get("public_name") or group["agency_name"])
        abbreviation = str(row.get("organisation_abbreviation") or agency_id)
        jurisdiction = str(row.get("jurisdiction") or "nz")
        candidates = handle_candidates(
            agency_id,
            abbreviation=abbreviation,
            jurisdiction=jurisdiction,
        )
        handle = str(row.get("handle") or "")
        mirrors.append(
            {
                "mirror_id": agency_id,
                "agency_id": agency_id,
                "agency_name": group["agency_name"],
                "public_name": public_name,
                "handle": handle,
                "handle_candidates": candidates,
                "handle_policy_version": row.get("handle_policy_version"),
                "organisation_abbreviation": abbreviation,
                "jurisdiction": jurisdiction,
                "url": str(row.get("url") or (f"https://bsky.app/profile/{handle}" if handle else "")),
                "environment": f"bluesky-mirror-{agency_id}",
                "registration_alias_slug": agency_id,
                "display_name": str(
                    row.get("display_name") or f"{public_name} Archive Mirror"
                ),
                "profile_disclosure": str(
                    row.get("profile_disclosure")
                    or f"Unofficial automated archive mirror. Not {group['agency_name']}."
                ),
                "source_ids": sorted(group["source_ids"]),
                "source_urls": sorted(group["source_urls"]),
                "source_platforms": sorted(group["source_platforms"]),
                "lifecycle_state": str(row.get("lifecycle_state") or "candidate"),
                "enabled": bool(row.get("enabled", False)),
                "backfill_state": str(row.get("backfill_state") or "not_started"),
                "health_state": str(row.get("health_state") or "not_checked"),
                "issue_number": row.get("issue_number"),
                "track_id": "bluesky_historical_backfill_rollout_20260721",
                "activated_at": row.get("activated_at"),
                "evidence": list(row.get("evidence") or []),
                "account_role": str(row.get("account_role") or "agency_mirror"),
            }
        )
    if not any(row["mirror_id"] == "nzgov-social-archive-index" for row in mirrors):
        mirrors.append(
            {
                "mirror_id": "nzgov-social-archive-index",
                "agency_id": "nzgov-social-archive-index",
                "agency_name": "New Zealand Government Social Media Corpus",
                "public_name": "NZ Government Social Media Archive",
                "handle": "",
                "handle_candidates": [
                    "nzgov-social-archive.bsky.social",
                    "nzgov-social-corpus-archive.bsky.social",
                ],
                "url": "",
                "environment": "bluesky-mirror-nzgov-social-archive-index",
                "registration_alias_slug": "nzgov-social-archive-index",
                "display_name": "NZ Government Social Media Archive Index",
                "profile_disclosure": "Unofficial index for automated government archive mirrors.",
                "source_ids": [],
                "source_urls": [],
                "source_platforms": [],
                "lifecycle_state": "candidate",
                "enabled": False,
                "backfill_state": "not_applicable",
                "health_state": "not_checked",
                "issue_number": None,
                "track_id": "bluesky_mirror_identity_governance_20260721",
                "activated_at": None,
                "evidence": [],
                "account_role": "corpus_index",
            }
        )
    mirrors.sort(key=lambda row: row["mirror_id"])
    result = {**existing, "mirrors": mirrors, "generated_at": _now()}
    validate_registry(result)
    return result


def write_registry(registry: Mapping[str, Any], path: str | Path = REGISTRY_PATH) -> None:
    validate_registry(registry)
    _write_json(Path(path), registry)


def workflow_matrix(
    registry: Mapping[str, Any],
    *,
    mode: str,
    mirror_id: str = "",
    runtime_state: Mapping[str, Any] | None = None,
) -> dict[str, list[dict[str, str]]]:
    runtime_accounts = (runtime_state or {}).get("accounts", {})
    rows = []
    for mirror in registry["mirrors"]:
        if mirror_id and mirror["mirror_id"] != mirror_id:
            continue
        if mode not in {"preflight", "health"} and not mirror.get("enabled"):
            continue
        if mode == "health" and mirror.get("lifecycle_state") not in {
            "preflight_ready",
            "backfilling",
            "live",
        }:
            continue
        if mode == "backfill" and mirror.get("backfill_state") == "complete":
            continue
        if mode == "backfill" and runtime_accounts.get(mirror["mirror_id"], {}).get(
            "backfill_complete"
        ):
            continue
        if mirror.get("lifecycle_state") in {"paused", "retired"}:
            continue
        rows.append(
            {
                "mirror_id": mirror["mirror_id"],
                "environment": mirror["environment"],
                "handle": mirror.get("handle", ""),
            }
        )
    if mode == "backfill":
        rows = rows[:1]
    return {"include": rows}


def preflight_account(
    registry: Mapping[str, Any],
    mirror_id: str,
    *,
    handle: str,
    app_password: str,
    login: Callable[[str, str], Any] | None = None,
    fetch_profile: Callable[[str], Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    account = _account(registry, mirror_id)
    if not handle or not app_password or handle != account.get("handle"):
        raise RuntimeError("Isolated Bluesky credentials are missing or mismatched.")
    if not BLUESKY_APP_PASSWORD_PATTERN.fullmatch(app_password):
        raise RuntimeError(
            "Bluesky automation requires a four-group app password; "
            "primary passwords are forbidden."
        )
    if login is None:
        from atproto import Client

        login = Client().login
    login(handle, app_password)
    profile = dict((fetch_profile or _fetch_public_profile)(handle))
    display_name = str(profile.get("displayName") or "")
    description = str(profile.get("description") or "")
    labels = {
        str(label.get("val") or "")
        for label in profile.get("labels", [])
        if isinstance(label, Mapping)
    }
    failures = []
    if "archive" not in display_name.casefold():
        failures.append("display name lacks archive disclosure")
    if "unofficial" not in description.casefold() or "archive" not in description.casefold():
        failures.append("description lacks unofficial archive disclosure")
    if "bot" not in labels:
        failures.append("bot self-label is missing")
    result = {
        "mirror_id": mirror_id,
        "handle": handle,
        "did": str(profile.get("did") or ""),
        "profile_url": f"https://bsky.app/profile/{handle}",
        "valid": not failures,
        "failures": failures,
        "checked_at": _now(),
    }
    if failures:
        raise RuntimeError("; ".join(failures))
    return result


def load_archive_records(
    account: Mapping[str, Any],
    root: str | Path = "historical_archive_normalized",
    *,
    eligibility_report_path: str | Path | None = None,
) -> list[MirrorRecord]:
    agency_id = str(account["agency_id"])
    records: dict[str, MirrorRecord] = {}
    decisions: list[SourceEligibilityResult] = []
    archive_root = Path(root)
    if not archive_root.exists():
        if eligibility_report_path:
            write_eligibility_report(account, decisions, eligibility_report_path)
        return []
    for shard in sorted(archive_root.rglob("*.jsonl")):
        for line in shard.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            raw = json.loads(line)
            decision = evaluate_source_eligibility(account, raw)
            decisions.append(decision)
            if not decision.eligible:
                continue
            content = str(raw.get("content") or raw.get("text") or raw.get("title") or "").strip()
            record_id = str(raw.get("record_id") or raw.get("post_id") or "")
            if not record_id or not content:
                continue
            record = MirrorRecord(
                record_id=record_id,
                agency_id=agency_id,
                source_id=decision.source_id,
                source_platform=decision.source_platform,
                created_at=str(raw.get("original_created_at") or raw.get("created_at") or ""),
                content=content,
                source_url=decision.source_url,
                public_name=str(
                    account.get("public_name") or account.get("agency_name") or ""
                ),
            )
            fingerprint = hashlib.sha256(
                f"{agency_id}\0{record.created_at[:10]}\0{content.casefold()}".encode()
            ).hexdigest()
            records.setdefault(fingerprint, record)
    if eligibility_report_path:
        write_eligibility_report(account, decisions, eligibility_report_path)
    return sorted(records.values(), key=lambda row: (row.created_at, row.record_id))


def normalize_source_platform(value: str) -> str:
    """Normalize supported source-platform aliases."""
    platform = value.strip().casefold()
    return {"twitter": "x"}.get(platform, platform)


def normalize_source_kind(value: str) -> str:
    """Normalize post-like record type aliases."""
    return value.strip().casefold().replace("-", "_")


def canonicalize_source_url(value: str) -> str:
    """Canonicalize a public source URL for policy comparison."""
    parsed = urlsplit(value.strip())
    if parsed.scheme.casefold() not in {"http", "https"} or not parsed.hostname:
        return ""
    host = parsed.hostname.casefold()
    if host.startswith("www."):
        host = host[4:]
    if host == "twitter.com":
        host = "x.com"
    path = re.sub(r"/+", "/", parsed.path).rstrip("/") or "/"
    return urlunsplit(("https", host, path, "", ""))


def evaluate_source_eligibility(
    account: Mapping[str, Any], raw: Mapping[str, Any]
) -> SourceEligibilityResult:
    """Evaluate one archive record against an explicit mirror allowlist."""
    source_id = str(raw.get("source_id") or "")
    agency_id = slugify(str(raw.get("agency_id") or ""))
    platform = normalize_source_platform(str(raw.get("source_platform") or ""))
    source_kind = normalize_source_kind(
        str(
            raw.get("source_kind")
            or raw.get("record_type")
            or raw.get("content_type")
            or ""
        )
    )
    source_url = str(
        raw.get("source_url") or raw.get("canonical_url") or raw.get("url") or ""
    )
    canonical_url = canonicalize_source_url(source_url)
    record_id = str(raw.get("record_id") or raw.get("post_id") or "")
    allowed_ids = {str(value) for value in (account.get("source_ids") or [])}
    allowed_platforms = {
        normalize_source_platform(str(value))
        for value in (account.get("source_platforms") or [])
    }
    allowed_hosts = {
        urlsplit(canonical).hostname
        for value in (account.get("source_urls") or [])
        if (canonical := canonicalize_source_url(str(value)))
    }
    excluded_urls = {
        canonicalize_source_url(str(value))
        for value in (account.get("excluded_source_urls") or [])
    }
    visibility = str(raw.get("visibility") or "").casefold()
    status = str(raw.get("status") or raw.get("archive_status") or "").casefold()
    reason = "accepted"
    if not source_id:
        reason = "missing_source_id"
    elif source_id not in allowed_ids:
        reason = "source_id_not_allowed"
    elif not agency_id or agency_id != str(account["agency_id"]):
        reason = "agency_mismatch"
    elif not platform:
        reason = "missing_source_platform"
    elif platform not in allowed_platforms:
        reason = "source_platform_not_allowed"
    elif not source_kind:
        reason = "missing_source_kind"
    elif source_kind not in MIRRORABLE_SOURCE_KINDS:
        reason = "source_kind_not_mirrorable"
    elif not visibility:
        reason = "missing_visibility"
    elif visibility != "public":
        reason = "visibility_not_public"
    elif status in TERMINAL_SOURCE_STATES or bool(raw.get("deleted")):
        reason = "terminal_source_state"
    elif not source_url:
        reason = "missing_source_url"
    elif not canonical_url:
        reason = "invalid_source_url"
    elif canonical_url in excluded_urls:
        reason = "source_url_excluded"
    elif allowed_hosts and urlsplit(canonical_url).hostname not in allowed_hosts:
        reason = "source_host_not_allowed"
    return SourceEligibilityResult(
        eligible=reason == "accepted",
        reason=reason,
        record_id=record_id,
        source_id=source_id,
        agency_id=agency_id,
        source_platform=platform,
        source_kind=source_kind,
        source_url=source_url,
    )


def write_eligibility_report(
    account: Mapping[str, Any],
    decisions: list[SourceEligibilityResult],
    path: str | Path,
) -> dict[str, Any]:
    """Persist bounded acceptance and rejection evidence for one mirror."""
    rejected = [decision for decision in decisions if not decision.eligible]
    reason_counts: dict[str, int] = {}
    for decision in rejected:
        reason_counts[decision.reason] = reason_counts.get(decision.reason, 0) + 1
    report = {
        "schema_version": 1,
        "generated_at": _now(),
        "mirror_id": str(account["mirror_id"]),
        "scanned": len(decisions),
        "accepted": sum(decision.eligible for decision in decisions),
        "rejected": len(rejected),
        "rejection_reason_counts": dict(sorted(reason_counts.items())),
        "rejection_examples": [
            {
                "record_id": decision.record_id,
                "source_id": decision.source_id,
                "agency_id": decision.agency_id,
                "source_platform": decision.source_platform,
                "source_kind": decision.source_kind,
                "source_url": decision.source_url,
                "reason": decision.reason,
            }
            for decision in rejected[:100]
        ],
        "rejection_examples_truncated": max(0, len(rejected) - 100),
    }
    _write_json(Path(path), report)
    return report


def render_record(record: MirrorRecord, *, historical: bool, limit: int = 300) -> str:
    date = record.created_at[:10] or "unknown date"
    public_name = f"[{record.public_name}] " if record.public_name else ""
    platform = "[linkedin] " if record.source_platform.casefold() == "linkedin" else ""
    prefix = (f"[Archived {date}] " if historical else "") + public_name + platform
    suffix = f"\n\nOriginal: {record.source_url}"
    available = max(0, limit - len(prefix) - len(suffix))
    body = record.content
    if len(body) > available:
        body = body[: max(0, available - 1)].rstrip() + "…"
    return f"{prefix}{body}{suffix}"


def render_thread(
    record: MirrorRecord,
    *,
    historical: bool,
    limit: int = 300,
    threshold: int = 280,
    max_parts: int = 4,
) -> list[str]:
    """Plan a bounded numbered thread without posting it.

    Threading is currently a planning primitive. Callers must explicitly opt
    in to posting the returned parts and persist one idempotency key for the
    complete thread before doing so.
    """
    single = render_record(record, historical=historical, limit=limit)
    if record.source_platform.casefold() != "linkedin" or len(single) <= threshold:
        return [single]
    public_name = f"[{record.public_name}] " if record.public_name else ""
    prefix = (
        (
            f"[Archived {record.created_at[:10] or 'unknown date'}] "
            if historical
            else ""
        )
        + public_name
        + "[linkedin] "
    )
    suffix = f"\n\nOriginal: {record.source_url}"
    available = max(1, limit - len(prefix) - len(suffix) - 12)
    words = record.content.split()
    if any(len(word) > available for word in words):
        return [single]
    chunks: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join(current + [word])
        if current and len(candidate) > available:
            chunks.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        chunks.append(" ".join(current))
    truncated = len(chunks) > max_parts
    chunks = chunks[:max_parts]
    if not chunks:
        return [single]
    if truncated:
        chunks[-1] = chunks[-1][: available - 1].rstrip() + "…"
    total = len(chunks)
    return [
        f"{prefix}[{index}/{total}] {chunk}{suffix if index == total else ''}"
        for index, chunk in enumerate(chunks, 1)
    ]


def publish_next(
    registry: Mapping[str, Any],
    mirror_id: str,
    *,
    mode: str,
    dry_run: bool = False,
    archive_root: str | Path = "historical_archive_normalized",
    state_path: str | Path = STATE_PATH,
    audit_path: str | Path = AUDIT_PATH,
    dead_letter_path: str | Path = DEAD_LETTER_PATH,
    eligibility_report_path: str | Path | None = None,
    sender: Callable[[BlueskyPost], SyndicationResult] | None = None,
    readback: Callable[[str], bool] | None = None,
) -> dict[str, Any]:
    account = _account(registry, mirror_id)
    state_file = _runtime_state_file(Path(state_path), mirror_id)
    audit_file = _account_event_file(Path(audit_path), AUDIT_PATH, AUDIT_DIR, mirror_id)
    dead_letter_file = _account_event_file(
        Path(dead_letter_path),
        DEAD_LETTER_PATH,
        DEAD_LETTER_DIR,
        mirror_id,
    )
    state = _load_json(state_file, {"accounts": {}})
    account_state = state.setdefault("accounts", {}).setdefault(mirror_id, {})
    if account_state.get("paused") and not dry_run:
        return {"mirror_id": mirror_id, "status": "paused", "posted": 0}
    if not dry_run:
        if os.getenv("BLUESKY_MIRRORING_ENABLED", "").casefold() != "true":
            return {"mirror_id": mirror_id, "status": "global_disabled", "posted": 0}
        if not account.get("enabled"):
            return {"mirror_id": mirror_id, "status": "account_disabled", "posted": 0}

    records = load_archive_records(
        account,
        archive_root,
        eligibility_report_path=eligibility_report_path,
    )
    posted_ids = set(account_state.get("posted_record_ids") or [])
    activated_at = str(account.get("activated_at") or "")
    historical = mode == "backfill"
    eligible = [
        row
        for row in records
        if row.record_id not in posted_ids
        and (historical or not activated_at or row.created_at >= activated_at)
    ]
    if historical and _posts_today(audit_file, mirror_id) >= 4:
        return {"mirror_id": mirror_id, "status": "daily_cap_reached", "posted": 0}
    if not eligible:
        if historical:
            account_state.update({"backfill_complete": True, "backfill_completed_at": _now()})
            _write_json(state_file, state)
        return {"mirror_id": mirror_id, "status": "no_eligible_records", "posted": 0}

    record = eligible[0]
    text = render_record(record, historical=historical)
    rendered_hash = hashlib.sha256(text.encode()).hexdigest()
    idempotency_key = hashlib.sha256(
        (
            f"v{PUBLICATION_STATE_VERSION}\0{mirror_id}\0{record.source_id}\0"
            f"{record.record_id}\0{rendered_hash}"
        ).encode()
    ).hexdigest()
    audit = {
        "mirror_id": mirror_id,
        "record_id": record.record_id,
        "source_id": record.source_id,
        "idempotency_key": idempotency_key,
        "rendered_hash": rendered_hash,
        "mode": mode,
        "attempted_at": _now(),
        "workflow_run": os.getenv("GITHUB_RUN_ID", "local"),
    }
    if dry_run:
        return {**audit, "status": "dry_run", "posted": 0, "text": text}

    handle = os.environ.get("BLUESKY_HANDLE", "")
    password = os.environ.get("BLUESKY_APP_PASSWORD", "")
    if not handle or not password or handle != account.get("handle"):
        raise RuntimeError("Account-isolated BLUESKY_HANDLE/BLUESKY_APP_PASSWORD are missing or mismatched.")
    publications = account_state.setdefault("publications", {})
    existing = publications.get(idempotency_key)
    if isinstance(existing, Mapping):
        return _reconcile_reserved_publication(
            state_file=state_file,
            state=state,
            account_state=account_state,
            publication=dict(existing),
            idempotency_key=idempotency_key,
            audit_path=audit_file,
            audit=audit,
            readback=readback or _public_readback,
        )

    publication = {
        **audit,
        "state": "planned",
        "planned_at": _now(),
        "reconciliation_attempts": 0,
        "uri": "",
        "cid": "",
    }
    publications[idempotency_key] = publication
    _append_jsonl(audit_file, {**publication, "status": "planned"})
    _write_json(state_file, state)

    post: BlueskyPost = {
        "post_id": record.record_id,
        "uri": "",
        "cid": "",
        "handle": record.agency_id,
        "author_did": "",
        "text": text,
        "created_at": record.created_at,
        "url": record.source_url,
        "images": [],
    }
    send = sender or _exact_bluesky_sender(handle, password)
    publication.update({"state": "submitted", "submitted_at": _now()})
    _append_jsonl(audit_file, {**publication, "status": "submitted"})
    _write_json(state_file, state)
    try:
        result = send(post)
    except Exception as error:
        publication.update(
            {
                "state": "pending_reconciliation",
                "detail": str(error),
                "reconciliation_attempts": 1,
                "last_reconciliation_at": _now(),
            }
        )
        _append_jsonl(
            audit_file,
            {**publication, "status": "pending_reconciliation"},
        )
        _write_json(state_file, state)
        return {
            **audit,
            "status": "pending_reconciliation",
            "posted": 0,
            "detail": str(error),
        }
    if not result.success or result.skipped:
        detail = result.detail or "posting was not accepted"
        publication.update({"state": "failed", "detail": detail, "failed_at": _now()})
        account_state.update(
            {"paused": True, "pause_reason": detail, "paused_at": _now()}
        )
        _append_jsonl(dead_letter_file, {**publication, "status": "failed"})
        _write_json(state_file, state)
        return {**audit, "status": "failed_paused", "posted": 0, "detail": detail}

    uri = result.detail
    publication.update(
        {
            "state": "pending_reconciliation",
            "uri": uri,
            "submitted_at": _now(),
        }
    )
    _append_jsonl(
        audit_file,
        {**publication, "status": "pending_reconciliation"},
    )
    _write_json(state_file, state)
    verify = readback or _public_readback
    reconciled = bool(uri.startswith("at://") and verify(uri))
    if not reconciled:
        publication.update(
            {
                "reconciliation_attempts": 1,
                "last_reconciliation_at": _now(),
            }
        )
        _append_jsonl(
            audit_file,
            {**publication, "status": "pending_reconciliation"},
        )
        _write_json(state_file, state)
        return {
            **audit,
            "status": "pending_reconciliation",
            "posted": 0,
            "uri": uri,
        }
    return _mark_publication_reconciled(
        state_file=state_file,
        state=state,
        account_state=account_state,
        publication=publication,
        idempotency_key=idempotency_key,
        audit_path=audit_file,
        audit=audit,
    )


def _reconcile_reserved_publication(
    *,
    state_file: Path,
    state: dict[str, Any],
    account_state: dict[str, Any],
    publication: dict[str, Any],
    idempotency_key: str,
    audit_path: Path,
    audit: Mapping[str, Any],
    readback: Callable[[str], bool],
) -> dict[str, Any]:
    """Resume a durable reservation without issuing another create request."""
    status = str(publication.get("state") or "")
    uri = str(publication.get("uri") or "")
    if status == "reconciled":
        return {
            **audit,
            "status": "already_reconciled",
            "posted": 0,
            "uri": uri,
        }
    attempts = int(publication.get("reconciliation_attempts") or 0) + 1
    reconciled = bool(uri.startswith("at://") and readback(uri))
    if reconciled:
        return _mark_publication_reconciled(
            state_file=state_file,
            state=state,
            account_state=account_state,
            publication=publication,
            idempotency_key=idempotency_key,
            audit_path=audit_path,
            audit=audit,
        )
    publication.update(
        {
            "state": "pending_reconciliation",
            "reconciliation_attempts": attempts,
            "last_reconciliation_at": _now(),
        }
    )
    account_state.setdefault("publications", {})[idempotency_key] = publication
    if attempts >= MAX_RECONCILIATION_ATTEMPTS:
        publication.update({"state": "failed", "failed_at": _now()})
        account_state.update(
            {
                "paused": True,
                "pause_reason": "publication reconciliation exhausted",
                "paused_at": _now(),
            }
        )
        result_status = "reconciliation_exhausted_paused"
    else:
        result_status = "pending_reconciliation"
    _append_jsonl(audit_path, {**publication, "status": result_status})
    _write_json(state_file, state)
    return {
        **audit,
        "status": result_status,
        "posted": 0,
        "uri": uri,
        "reconciliation_attempts": attempts,
    }


def _mark_publication_reconciled(
    *,
    state_file: Path,
    state: dict[str, Any],
    account_state: dict[str, Any],
    publication: dict[str, Any],
    idempotency_key: str,
    audit_path: Path,
    audit: Mapping[str, Any],
) -> dict[str, Any]:
    uri = str(publication.get("uri") or "")
    publication.update(
        {
            "state": "reconciled",
            "reconciled_at": _now(),
            "last_reconciliation_at": _now(),
        }
    )
    account_state.setdefault("publications", {})[idempotency_key] = publication
    posted_ids = account_state.setdefault("posted_record_ids", [])
    if audit["record_id"] not in posted_ids:
        posted_ids.append(audit["record_id"])
    account_state.update(
        {"last_success_at": _now(), "last_uri": uri, "backfill_complete": False}
    )
    _append_jsonl(
        audit_path,
        {
            **publication,
            "publication_state": "reconciled",
            "status": "posted",
            "reconciled": True,
        },
    )
    _write_json(state_file, state)
    return {**audit, "status": "posted", "posted": 1, "uri": uri}


def pause(state_path: str | Path, mirror_id: str, reason: str) -> dict[str, Any]:
    path = Path(state_path)
    targets: Iterable[str]
    if mirror_id == "all":
        registry = load_registry()
        targets = [row["mirror_id"] for row in registry["mirrors"]]
    else:
        targets = [mirror_id]
    aggregate = {"accounts": {}}
    for target in targets:
        target_path = _runtime_state_file(path, target)
        state = _load_json(target_path, {"accounts": {}})
        state.setdefault("accounts", {}).setdefault(target, {}).update(
            {"paused": True, "pause_reason": reason, "paused_at": _now()}
        )
        _write_json(target_path, state)
        aggregate["accounts"][target] = state["accounts"][target]
    return aggregate


def recover_account(
    registry: Mapping[str, Any],
    mirror_id: str,
    *,
    apply: bool = False,
    state_path: str | Path = STATE_PATH,
    report_path: str | Path | None = None,
    probe: Callable[[str], str] | None = None,
) -> dict[str, Any]:
    """Diagnose a paused mirror and resume only with deterministic evidence."""
    _account(registry, mirror_id)
    state_file = _runtime_state_file(Path(state_path), mirror_id)
    state = _load_json(state_file, {"accounts": {}})
    account_state = state.setdefault("accounts", {}).setdefault(mirror_id, {})
    publications = account_state.get("publications") or {}
    check = probe or _public_recovery_probe
    evidence = []
    unresolved = False
    changed = False
    for key, raw_publication in sorted(publications.items()):
        publication = dict(raw_publication)
        uri = str(publication.get("uri") or "")
        publication_state = str(publication.get("state") or "")
        if publication_state == "reconciled":
            classification = "reconciled"
        elif not uri:
            classification = "ambiguous_missing_uri"
            unresolved = True
        else:
            classification = check(uri)
            if classification == "reconciled":
                if apply:
                    publication.update(
                        {
                            "state": "reconciled",
                            "reconciled_at": _now(),
                            "last_reconciliation_at": _now(),
                        }
                    )
                    publications[key] = publication
                    record_id = str(publication.get("record_id") or "")
                    posted_ids = account_state.setdefault("posted_record_ids", [])
                    if record_id and record_id not in posted_ids:
                        posted_ids.append(record_id)
                    changed = True
            else:
                unresolved = True
        evidence.append(
            {
                "idempotency_key": key,
                "record_id": str(publication.get("record_id") or ""),
                "uri": uri,
                "publication_state": publication_state,
                "classification": classification,
            }
        )

    pause_reason = str(account_state.get("pause_reason") or "")
    recoverable_reason = pause_reason in {
        "public readback failed",
        "publication reconciliation exhausted",
    }
    can_resume = bool(account_state.get("paused")) and recoverable_reason and not unresolved
    resumed = False
    if apply and can_resume:
        account_state.update(
            {
                "paused": False,
                "pause_reason": "",
                "resumed_at": _now(),
                "recovery_evidence_count": len(evidence),
            }
        )
        resumed = True
        changed = True
    if changed:
        _write_json(state_file, state)
    result = {
        "schema_version": 1,
        "mirror_id": mirror_id,
        "diagnosed_at": _now(),
        "apply_requested": apply,
        "paused": bool(account_state.get("paused")),
        "pause_reason": pause_reason,
        "recoverable_reason": recoverable_reason,
        "can_resume": can_resume,
        "resumed": resumed,
        "evidence": evidence,
        "status": (
            "resumed"
            if resumed
            else "ready_to_resume"
            if can_resume
            else "recovery_blocked"
            if account_state.get("paused")
            else "not_paused"
        ),
    }
    output = Path(
        report_path or (RECOVERY_REPORT_DIR / f"{slugify(mirror_id, maximum=80)}.json")
    )
    _write_json(output, result)
    return result


def credential_health_report(
    registry: Mapping[str, Any],
    mirror_id: str,
    *,
    handle: str,
    app_password: str,
) -> dict[str, Any]:
    """Return nonsecret credential configuration evidence."""
    account = _account(registry, mirror_id)
    handle_matches = bool(handle and handle == account.get("handle"))
    app_password_format = bool(
        app_password and BLUESKY_APP_PASSWORD_PATTERN.fullmatch(app_password)
    )
    return {
        "schema_version": 1,
        "mirror_id": mirror_id,
        "checked_at": _now(),
        "credential_mode": "app_password" if app_password_format else "invalid",
        "handle_present": bool(handle),
        "handle_matches_registry": handle_matches,
        "app_password_present": bool(app_password),
        "app_password_format_valid": app_password_format,
        "valid": handle_matches and app_password_format,
    }


def health_report(
    registry: Mapping[str, Any],
    *,
    runtime_state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    client = BlueskyApiClient()
    runtime_accounts = (runtime_state or load_runtime_state()).get("accounts", {})
    rows = []
    for account in registry["mirrors"]:
        handle = str(account.get("handle") or "")
        if not handle:
            rows.append(
                {
                    "mirror_id": account["mirror_id"],
                    "status": "account_not_created",
                    "runtime_state": runtime_accounts.get(account["mirror_id"], {}),
                }
            )
            continue
        try:
            feed = client.fetch_author_feed(handle, limit=1)
            rows.append(
                {
                    "mirror_id": account["mirror_id"],
                    "handle": handle,
                    "status": "publicly_resolvable",
                    "visible_posts": len(feed),
                    "runtime_state": runtime_accounts.get(account["mirror_id"], {}),
                }
            )
        except Exception as error:
            rows.append(
                {
                    "mirror_id": account["mirror_id"],
                    "handle": handle,
                    "status": "fault",
                    "detail": str(error),
                    "runtime_state": runtime_accounts.get(account["mirror_id"], {}),
                }
            )
    rows.sort(key=lambda row: str(row["mirror_id"]))
    return {"generated_at": _now(), "accounts": rows}


def migrate_runtime_state(
    monolithic_path: str | Path = STATE_PATH,
    state_dir: str | Path = STATE_DIR,
) -> dict[str, Any]:
    """Partition a legacy state file without overwriting existing account state."""
    source = Path(monolithic_path)
    destination = Path(state_dir)
    legacy = _load_json(source, {"accounts": {}})
    migrated = []
    preserved = []
    for mirror_id, account_state in sorted(legacy.get("accounts", {}).items()):
        target = destination / f"{slugify(str(mirror_id), maximum=80)}.json"
        if target.exists():
            preserved.append(str(mirror_id))
            continue
        _write_json(
            target,
            {
                "schema_version": 1,
                "mirror_id": str(mirror_id),
                "accounts": {str(mirror_id): account_state},
            },
        )
        migrated.append(str(mirror_id))
    return {
        "schema_version": 1,
        "migrated": migrated,
        "preserved": preserved,
        "source": str(source),
        "state_dir": str(destination),
    }


def load_runtime_state(
    monolithic_path: str | Path = STATE_PATH,
    state_dir: str | Path = STATE_DIR,
) -> dict[str, Any]:
    """Load deterministic aggregate runtime state from account partitions."""
    source = Path(monolithic_path)
    directory = Path(state_dir)
    if source.exists():
        migrate_runtime_state(source, directory)
    accounts: dict[str, Any] = {}
    if directory.exists():
        for path in sorted(directory.glob("*.json")):
            partition = _load_json(path, {"accounts": {}})
            for mirror_id, account_state in partition.get("accounts", {}).items():
                if mirror_id in accounts:
                    raise ValueError(f"Duplicate runtime state partition: {mirror_id}")
                accounts[str(mirror_id)] = account_state
    return {
        "schema_version": 1,
        "generated_at": _now(),
        "accounts": dict(sorted(accounts.items())),
    }


def write_programme_report(registry: Mapping[str, Any], path: str | Path = REPORT_PATH) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for row in registry["mirrors"]:
        state = str(row["lifecycle_state"])
        counts[state] = counts.get(state, 0) + 1
    report = {
        "schema_version": 1,
        "generated_at": _now(),
        "programme_issue": registry.get("programme_issue"),
        "total_identities": len(registry["mirrors"]),
        "lifecycle_counts": counts,
        "enabled_accounts": sum(bool(row.get("enabled")) for row in registry["mirrors"]),
        "posting_default": "disabled",
        "archive_workflows_post": False,
    }
    _write_json(Path(path), report)
    return report


def _manifest_rows(manifest: Mapping[str, Any] | list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    if isinstance(manifest, list):
        return manifest
    for key in ("sources", "candidates", "records"):
        value = manifest.get(key)
        if isinstance(value, list):
            return value
    return []


def _account(registry: Mapping[str, Any], mirror_id: str) -> Mapping[str, Any]:
    for account in registry["mirrors"]:
        if account["mirror_id"] == mirror_id:
            return account
    raise KeyError(f"Unknown mirror_id: {mirror_id}")


def _public_readback(uri: str) -> bool:
    client = BlueskyApiClient(base_url="https://public.api.bsky.app", timeout_seconds=15)
    for attempt in range(6):
        try:
            if any(str(post.get("uri") or "") == uri for post in client.fetch_posts([uri])):
                return True
        except Exception:
            pass
        if attempt < 5:
            time.sleep(2**attempt)
    return False


def _public_recovery_probe(uri: str) -> str:
    client = BlueskyApiClient(base_url="https://public.api.bsky.app", timeout_seconds=15)
    try:
        posts = client.fetch_posts([uri])
    except Exception:
        return "ambiguous"
    if any(str(post.get("uri") or "") == uri for post in posts):
        return "reconciled"
    return "deleted_or_missing"


def _exact_bluesky_sender(
    handle: str, app_password: str
) -> Callable[[BlueskyPost], SyndicationResult]:
    from atproto import Client

    client = Client()
    client.login(handle, app_password)

    def send(post: BlueskyPost) -> SyndicationResult:
        response = client.send_post(text=post["text"])
        uri = str(getattr(response, "uri", "") or "")
        return SyndicationResult("bluesky", success=bool(uri), detail=uri)

    return send


def _fetch_public_profile(handle: str) -> Mapping[str, Any]:
    query = urlencode({"actor": handle})
    request = Request(
        f"https://public.api.bsky.app/xrpc/app.bsky.actor.getProfile?{query}",
        headers={"Accept": "application/json"},
    )
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def _posts_today(path: Path, mirror_id: str) -> int:
    if not path.exists():
        return 0
    today = datetime.now(UTC).date().isoformat()
    count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("mirror_id") == mirror_id and str(row.get("attempted_at", "")).startswith(today) and row.get("status") == "posted":
            count += 1
    return count


def _load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def _runtime_state_file(base_path: Path, mirror_id: str) -> Path:
    if base_path == STATE_PATH:
        if STATE_PATH.exists():
            migrate_runtime_state()
        return STATE_DIR / f"{slugify(mirror_id, maximum=80)}.json"
    return base_path


def _account_event_file(
    requested_path: Path,
    legacy_path: Path,
    directory: Path,
    mirror_id: str,
) -> Path:
    if requested_path == legacy_path:
        return directory / f"{slugify(mirror_id, maximum=80)}.jsonl"
    return requested_path


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _append_jsonl(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")


def _now() -> str:
    return datetime.now(UTC).isoformat()
