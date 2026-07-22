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
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from src.bluesky import BlueskyApiClient, BlueskyPost
from src.syndication import SyndicationResult

REGISTRY_PATH = Path("config/mirror_accounts.json")
STATE_PATH = Path("conductor/bluesky_mirror_runtime_state.json")
AUDIT_PATH = Path("conductor/bluesky_mirror_post_audit.jsonl")
DEAD_LETTER_PATH = Path("conductor/bluesky_mirror_dead_letter.jsonl")
REPORT_PATH = Path("conductor/bluesky_mirror_programme_report.json")
SOCIAL_PLATFORMS = {
    "activitypub",
    "bluesky",
    "facebook",
    "instagram",
    "medium",
    "substack",
    "threads",
    "x",
    "youtube",
}
TERMINAL_SOURCE_STATES = {"deleted", "private", "withdrawn", "unverifiable"}
SECRET_FIELD_PATTERN = re.compile(r"password|secret|token|cookie|verification", re.I)
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


@dataclass(frozen=True)
class MirrorRecord:
    record_id: str
    agency_id: str
    source_id: str
    source_platform: str
    created_at: str
    content: str
    source_url: str


def slugify(value: str, *, maximum: int = 40) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return slug[:maximum].rstrip("-") or "agency"


def handle_candidates(agency_id: str) -> list[str]:
    slug = slugify(agency_id, maximum=38)
    return [f"{slug}-archive.bsky.social", f"nzgov-{slug}-archive.bsky.social"]


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
        if not mirror_id or mirror_id in seen_ids:
            raise ValueError(f"Missing or duplicate mirror_id: {mirror_id}")
        if handle and handle in seen_handles:
            raise ValueError(f"Duplicate mirror handle: {handle}")
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
        candidates = handle_candidates(agency_id)
        handle = str(row.get("handle") or "")
        mirrors.append(
            {
                "mirror_id": agency_id,
                "agency_id": agency_id,
                "agency_name": group["agency_name"],
                "handle": handle,
                "handle_candidates": candidates,
                "url": str(row.get("url") or (f"https://bsky.app/profile/{handle}" if handle else "")),
                "environment": f"bluesky-mirror-{agency_id}",
                "registration_alias_slug": agency_id,
                "display_name": str(
                    row.get("display_name") or f"{group['agency_name']} Archive Mirror"
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
    account: Mapping[str, Any], root: str | Path = "historical_archive_normalized"
) -> list[MirrorRecord]:
    source_ids = set(account.get("source_ids") or [])
    agency_id = str(account["agency_id"])
    records: dict[str, MirrorRecord] = {}
    archive_root = Path(root)
    if not archive_root.exists():
        return []
    for shard in sorted(archive_root.rglob("*.jsonl")):
        for line in shard.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            raw = json.loads(line)
            raw_source_id = str(raw.get("source_id") or "")
            raw_agency_id = slugify(str(raw.get("agency_id") or ""))
            if raw_source_id not in source_ids and raw_agency_id != agency_id:
                continue
            visibility = str(raw.get("visibility") or "public").casefold()
            status = str(raw.get("status") or raw.get("archive_status") or "").casefold()
            if visibility != "public" or status in TERMINAL_SOURCE_STATES or raw.get("deleted"):
                continue
            content = str(raw.get("content") or raw.get("text") or raw.get("title") or "").strip()
            source_url = str(raw.get("source_url") or raw.get("canonical_url") or raw.get("url") or "")
            record_id = str(raw.get("record_id") or raw.get("post_id") or "")
            if not record_id or not content or not source_url:
                continue
            record = MirrorRecord(
                record_id=record_id,
                agency_id=agency_id,
                source_id=raw_source_id,
                source_platform=str(raw.get("source_platform") or shard.parent.name),
                created_at=str(raw.get("original_created_at") or raw.get("created_at") or ""),
                content=content,
                source_url=source_url,
            )
            fingerprint = hashlib.sha256(
                f"{agency_id}\0{record.created_at[:10]}\0{content.casefold()}".encode()
            ).hexdigest()
            records.setdefault(fingerprint, record)
    return sorted(records.values(), key=lambda row: (row.created_at, row.record_id))


def render_record(record: MirrorRecord, *, historical: bool, limit: int = 300) -> str:
    date = record.created_at[:10] or "unknown date"
    prefix = f"[Archived {date}] " if historical else ""
    suffix = f"\n\nOriginal: {record.source_url}"
    available = max(0, limit - len(prefix) - len(suffix))
    body = record.content
    if len(body) > available:
        body = body[: max(0, available - 1)].rstrip() + "…"
    return f"{prefix}{body}{suffix}"


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
    sender: Callable[[BlueskyPost], SyndicationResult] | None = None,
    readback: Callable[[str], bool] | None = None,
) -> dict[str, Any]:
    account = _account(registry, mirror_id)
    state_file = Path(state_path)
    state = _load_json(state_file, {"accounts": {}})
    account_state = state.setdefault("accounts", {}).setdefault(mirror_id, {})
    if account_state.get("paused"):
        return {"mirror_id": mirror_id, "status": "paused", "posted": 0}
    if not dry_run:
        if os.getenv("BLUESKY_MIRRORING_ENABLED", "").casefold() != "true":
            return {"mirror_id": mirror_id, "status": "global_disabled", "posted": 0}
        if not account.get("enabled"):
            return {"mirror_id": mirror_id, "status": "account_disabled", "posted": 0}

    records = load_archive_records(account, archive_root)
    posted_ids = set(account_state.get("posted_record_ids") or [])
    activated_at = str(account.get("activated_at") or "")
    historical = mode == "backfill"
    eligible = [
        row
        for row in records
        if row.record_id not in posted_ids
        and (historical or not activated_at or row.created_at >= activated_at)
    ]
    if historical and _posts_today(Path(audit_path), mirror_id) >= 4:
        return {"mirror_id": mirror_id, "status": "daily_cap_reached", "posted": 0}
    if not eligible:
        if historical:
            account_state.update({"backfill_complete": True, "backfill_completed_at": _now()})
            _write_json(state_file, state)
        return {"mirror_id": mirror_id, "status": "no_eligible_records", "posted": 0}

    record = eligible[0]
    text = render_record(record, historical=historical)
    rendered_hash = hashlib.sha256(text.encode()).hexdigest()
    audit = {
        "mirror_id": mirror_id,
        "record_id": record.record_id,
        "source_id": record.source_id,
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
    result: SyndicationResult | None = None
    failure = ""
    for attempt in range(1, 4):
        try:
            result = send(post)
            if result.success and not result.skipped:
                break
            failure = result.detail or "posting failed"
        except Exception as error:  # bounded workflow isolation
            failure = str(error)
        if attempt < 3:
            time.sleep(2 ** (attempt - 1))
    if result is None or not result.success or result.skipped:
        account_state.update({"paused": True, "pause_reason": failure, "paused_at": _now()})
        _append_jsonl(Path(dead_letter_path), {**audit, "status": "failed", "detail": failure})
        _write_json(state_file, state)
        return {**audit, "status": "failed_paused", "posted": 0, "detail": failure}

    uri = result.detail
    verify = readback or _public_readback
    reconciled = bool(uri.startswith("at://") and verify(uri))
    status = "posted" if reconciled else "reconcile_failed"
    _append_jsonl(Path(audit_path), {**audit, "status": status, "uri": uri, "reconciled": reconciled})
    if not reconciled:
        account_state.update(
            {"paused": True, "pause_reason": "public readback failed", "paused_at": _now()}
        )
        _write_json(state_file, state)
        return {**audit, "status": "reconcile_failed_paused", "posted": 0, "uri": uri}
    account_state.setdefault("posted_record_ids", []).append(record.record_id)
    account_state.update(
        {"last_success_at": _now(), "last_uri": uri, "backfill_complete": False}
    )
    _write_json(state_file, state)
    return {**audit, "status": "posted", "posted": 1, "uri": uri}


def pause(state_path: str | Path, mirror_id: str, reason: str) -> dict[str, Any]:
    path = Path(state_path)
    state = _load_json(path, {"accounts": {}})
    targets: Iterable[str]
    if mirror_id == "all":
        registry = load_registry()
        targets = [row["mirror_id"] for row in registry["mirrors"]]
    else:
        targets = [mirror_id]
    for target in targets:
        state.setdefault("accounts", {}).setdefault(target, {}).update(
            {"paused": True, "pause_reason": reason, "paused_at": _now()}
        )
    _write_json(path, state)
    return state


def health_report(registry: Mapping[str, Any]) -> dict[str, Any]:
    client = BlueskyApiClient()
    rows = []
    for account in registry["mirrors"]:
        handle = str(account.get("handle") or "")
        if not handle:
            rows.append({"mirror_id": account["mirror_id"], "status": "account_not_created"})
            continue
        try:
            feed = client.fetch_author_feed(handle, limit=1)
            rows.append(
                {
                    "mirror_id": account["mirror_id"],
                    "handle": handle,
                    "status": "publicly_resolvable",
                    "visible_posts": len(feed),
                }
            )
        except Exception as error:
            rows.append({"mirror_id": account["mirror_id"], "handle": handle, "status": "fault", "detail": str(error)})
    return {"generated_at": _now(), "accounts": rows}


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
    return any(str(post.get("uri") or "") == uri for post in BlueskyApiClient().fetch_posts([uri]))


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


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _append_jsonl(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")


def _now() -> str:
    return datetime.now(UTC).isoformat()
