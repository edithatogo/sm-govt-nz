"""Build the canonical completion matrix and deterministic archive work queue."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
TRACK_ID = "govt_archive_all_source_completion_20260713"
LIFECYCLE_STATES = {
    "discovered", "rejected_not_government", "registered", "scheduled", "capturing",
    "archived", "terminal_empty", "terminal_deleted", "terminal_invalid",
    "terminal_external_access", "automation_fault",
}
COMPLETE_STATES = {
    "archived", "rejected_not_government", "terminal_empty", "terminal_deleted",
    "terminal_invalid", "terminal_external_access",
}
SUCCESS_STATUSES = {
    "already_captured", "browser_already_captured", "browser_captured", "captured",
    "feed_already_captured", "feed_captured", "manual_seed_captured",
    "public_snapshot_already_captured", "public_snapshot_captured",
}
EMPTY_STATUSES = {"no_records", "browser_no_visible_content", "browser_no_visible_posts"}
DELETED_STATUSES = {"not_found", "youtube_channel_not_found", "youtube_video_not_found"}
INVALID_STATUSES = {"source_url_not_channel", "invalid", "seed_invalid", "seed_empty"}
EXTERNAL_STATUSES = {
    "needs_authorized_seed_or_api", "manual_seed_missing", "threads_api_error",
    "threads_permission_error", "browser_login_required", "browser_captcha_or_challenge",
    "auth_required",
}
ACTIONABLE_FAILURE_STATUSES = {
    "capture_blocked", "http_error", "network_error", "network_timeout", "not_acceptable",
    "tls_failed", "capture_failed", "browser_capture_failed",
}
REPORT_NAMES = [
    "rss_archive_report.json", "json_feed_archive_report.json", "api_archive_report.json",
    "bluesky_archive_report.json", "youtube_archive_report.json", "website_archive_report.json",
    "website_page_archive_report.json", "website_browser_archive_report.json",
    "threads_archive_report.json", "x_archive_report.json", "x_feed_archive_report.json",
    "x_browser_and_feed_archive_report.json", "linkedin_archive_report.json",
    "facebook_archive_report.json",
    "newsletter_archive_report.json", "manual_seed_onboarding_report.json",
]
WORKFLOWS = {
    "linkedin": "archive_registered_sources.yml",
    "website_page": "archive_website_browser_fallback.yml",
    "youtube": "archive_youtube_scheduled.yml",
    "newsletter": "govt_source_discovery.yml",
    "medium": "govt_source_discovery.yml",
    "substack": "govt_source_discovery.yml",
    "rss": "archive_rss_scheduled.yml",
    "json_feed": "archive_json_feed_scheduled.yml",
    "api": "archive_registered_sources.yml",
    "bluesky": "archive_bluesky_scheduled.yml",
    "x": "archive_registered_sources.yml",
    "threads": "archive_threads_scheduled.yml",
}
ADAPTERS = {
    "linkedin": "public_snapshot_or_authorized_seed",
    "website_page": "public_http_then_playwright",
    "youtube": "public_channel_feed_and_metadata",
    "newsletter": "public_feed_discovery_or_authorized_seed",
    "medium": "rss_feed",
    "substack": "rss_feed",
    "rss": "rss_atom",
    "json_feed": "json_feed",
    "api": "public_http_api",
    "bluesky": "atproto_public_api",
    "x": "nitter_compatible_feed_then_browser",
    "threads": "authorized_seed_or_opt_in_api",
    "facebook": "authorized_seed_or_approved_api",
    "instagram": "authorized_seed_or_approved_api",
}
PRIORITY = {"linkedin": 10, "website_page": 20, "youtube": 30, "newsletter": 40, "medium": 41, "substack": 42}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def source_key(row: dict[str, Any]) -> str:
    return str(row.get("candidate_id") or row.get("source_id") or "")


def canonical_url_key(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    parsed = urlsplit(raw)
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, parsed.query, ""))


def alternative_capture_url_keys(row: dict[str, Any]) -> list[str]:
    url = str(row.get("url") or "")
    platform = str(row.get("platform") or row.get("source_type") or "")
    keys = [canonical_url_key(url)]
    if platform == "medium" and url:
        parsed = urlsplit(url)
        if parsed.netloc.lower() == "medium.com" and parsed.path.startswith("/@"):
            keys.append(canonical_url_key(f"https://medium.com/feed{parsed.path.rstrip('/')}"))
        elif parsed.netloc.lower().endswith(".medium.com"):
            keys.append(canonical_url_key(f"{url.rstrip('/')}/feed"))
    return [key for key in dict.fromkeys(keys) if key]


def report_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    rows = report.get("results") or report.get("items") or []
    return [row for row in rows if isinstance(row, dict)]


def status_rank(status: str) -> int:
    if status in SUCCESS_STATUSES:
        return 100
    if status == "seed_present":
        return 70
    if status in EMPTY_STATUSES | DELETED_STATUSES | INVALID_STATUSES:
        return 80
    if status == "public_fallback_available":
        return 70
    if status in ACTIONABLE_FAILURE_STATUSES:
        return 75
    if status in EXTERNAL_STATUSES:
        return 70
    return 0


def build_report_index(conductor: Path) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    report_paths = [conductor / name for name in REPORT_NAMES]
    report_paths.extend(sorted(conductor.glob("*_archive_offset_*_report.json")))
    for path in dict.fromkeys(report_paths):
        report = load_json(path, {})
        for row in report_rows(report):
            key = source_key(row)
            if not key:
                continue
            status = str(row.get("status") or row.get("onboarding_status") or "unknown")
            candidate = {**row, "status": status, "evidence_report": path.as_posix()}
            if key not in index or status_rank(status) >= status_rank(str(index[key].get("status") or "")):
                index[key] = candidate
    return index


def normalized_counts(root: Path) -> Counter[str]:
    counts: Counter[str] = Counter()
    if not root.is_dir():
        return counts
    for path in root.rglob("*.jsonl"):
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip() or line.startswith("version https://git-lfs"):
                    continue
                record = json.loads(line)
                cross_ids = record.get("cross_source_ids") or {}
                key = str(cross_ids.get("source_id") or record.get("source_id") or "")
                if key:
                    counts[key] += 1
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
    return counts


def publication_evidence(conductor: Path) -> tuple[str, list[str]]:
    paths = [conductor / "archive_publication_status.json", conductor / "monthly_release_ledger.json"]
    evidence = [path.as_posix() for path in paths if path.is_file()]
    return ("dataset_publication_evidence_present" if evidence else "publication_evidence_missing", evidence)


def classify_state(
    row: dict[str, Any], registered: bool, evidence: dict[str, Any], normalized_count: int
) -> tuple[str, str]:
    status = str(evidence.get("status") or "")
    readiness = str(row.get("readiness") or "discovered")
    platform = str(row.get("platform") or row.get("source_type") or "unknown")
    heuristic_common_path = str(row.get("origin") or "") == "configured_common_path"
    if normalized_count > 0 or status in SUCCESS_STATUSES:
        return "archived", "archive_evidence"
    if status in EMPTY_STATUSES:
        return "terminal_empty", "source_returned_no_records"
    if status in DELETED_STATUSES or readiness == "retired":
        return "terminal_deleted", "source_or_content_not_found"
    if status in INVALID_STATUSES:
        return "terminal_invalid", "invalid_source_or_input"
    if status == "rejected_not_government":
        return "rejected_not_government", "evidence_backed_scope_rejection"
    if status == "seed_present" or status == "public_fallback_available":
        return "scheduled", "capture_input_available"
    reason = str(evidence.get("reason") or evidence.get("error") or "")
    if platform == "linkedin" and status == "http_error" and (
        "HTTP 429" in reason or "HTTP 999" in reason
    ):
        return "terminal_external_access", "linkedin_public_access_rate_limited"
    if heuristic_common_path and status == "dns_failed":
        return "terminal_deleted", "heuristic_endpoint_domain_unavailable"
    if heuristic_common_path and status in {"method_not_allowed", "not_acceptable", "tls_failed"}:
        return "terminal_invalid", "heuristic_endpoint_invalid"
    if heuristic_common_path and status in {"capture_failed", "network_timeout"}:
        return "terminal_invalid", "heuristic_endpoint_exhausted_public_retries"
    if heuristic_common_path and status == "capture_blocked":
        return "terminal_external_access", "heuristic_endpoint_public_access_blocked"
    if platform == "website_page" and status == "dns_failed":
        return "terminal_deleted", "website_domain_unavailable"
    if platform == "website_page" and status == "method_not_allowed":
        return "terminal_invalid", "website_rejected_capture_method_after_fallback"
    if platform == "website_page" and status in {
        "capture_blocked", "http_error", "network_error", "network_timeout",
    }:
        return "terminal_external_access", "website_exhausted_http_and_browser_fallbacks"
    if status in ACTIONABLE_FAILURE_STATUSES:
        return "automation_fault", status
    if status in EXTERNAL_STATUSES or readiness in {"blocked_credential", "blocked_legal"}:
        return "terminal_external_access", status or readiness
    if registered:
        return ("scheduled" if platform in WORKFLOWS else "registered"), "registered_source"
    return "discovered", "candidate_requires_classification"


def dispatch_for(row: dict[str, Any], state: str) -> dict[str, Any]:
    platform = str(row.get("platform") or row.get("source_type") or "unknown")
    workflow = WORKFLOWS.get(platform, "")
    if platform == "website_page" and state == "scheduled":
        workflow = "archive_registered_sources.yml"
    inputs: dict[str, str] = {}
    if workflow == "archive_registered_sources.yml":
        offset = 100 * (int(row.get("_manifest_offset") or 0) // 100)
        inputs = {"source_type": platform, "agency_id": "", "include_blocked": "true", "dry_run": "false", "limit_sources": "100", "offset_sources": str(offset), "publish": "false", "commit_payloads": "true"}
    elif workflow == "archive_website_browser_fallback.yml":
        offset = 10 * (int(row.get("_queue_offset") or 0) // 10)
        inputs = {"agency_id": "", "dry_run": "false", "limit_sources": "10", "offset_sources": str(offset), "eligible_statuses": "capture_blocked,method_not_allowed,network_error,network_timeout,not_acceptable,tls_failed", "per_page_timeout": "45", "commit_payloads": "true", "publish": "false"}
    elif workflow == "archive_youtube_scheduled.yml":
        inputs = {"agency_id": "", "dry_run": "false", "channel_limit": "50"}
    elif workflow in {
        "archive_rss_scheduled.yml",
        "archive_json_feed_scheduled.yml",
        "archive_bluesky_scheduled.yml",
    }:
        inputs = {"agency_id": "", "dry_run": "false", "commit_payloads": "true"}
    return {"workflow": workflow, "inputs": inputs, "dispatchable": bool(workflow and inputs)}


def next_action(row: dict[str, Any], state: str) -> tuple[str, str]:
    platform = str(row.get("platform") or row.get("source_type") or "unknown")
    if state == "archived":
        return "monitor_ongoing_capture", "new records remain scheduled and publish monthly"
    if state == "terminal_external_access":
        return "monitor_for_authorized_input", "reopen automatically when seed or approved API becomes available"
    if state in COMPLETE_STATES:
        return "retain_terminal_evidence", "terminal evidence remains machine verifiable"
    if state == "discovered":
        return "classify_and_promote_candidate", "register a verified government source or reject with evidence"
    if platform == "linkedin":
        return "capture_public_linkedin_snapshot", "archived record or evidence-backed terminal status"
    if platform == "website_page":
        return "retry_public_website_capture", "archived browser/HTTP record or terminal evidence"
    if platform == "youtube":
        return "resolve_youtube_source", "archived channel metadata or deleted/invalid tombstone"
    if platform in {"newsletter", "medium", "substack"}:
        return "discover_public_feed_or_archive", "registered feed/archive capture or external-access terminal state"
    return "run_registered_source_adapter", "archived evidence or an evidence-backed terminal state"


def build_completion_matrix(
    readiness: dict[str, Any], manifest: dict[str, Any], report_index: dict[str, dict[str, Any]],
    normalized: Counter[str], conductor: Path, prior_matrix: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    readiness_rows = readiness.get("sources", [])
    manifest_rows = manifest.get("sources", [])
    manifest_by_id = {source_key(row): row for row in manifest_rows if source_key(row)}
    manifest_by_url = {
        canonical_url_key(row.get("url")): row
        for row in manifest_rows
        if canonical_url_key(row.get("url"))
    }
    manifest_offsets_by_id: dict[str, int] = {}
    manifest_offsets_by_url: dict[str, int] = {}
    platform_offsets: Counter[str] = Counter()
    for manifest_source in manifest_rows:
        manifest_platform = str(manifest_source.get("platform") or manifest_source.get("source_type") or "unknown")
        offset = platform_offsets[manifest_platform]
        platform_offsets[manifest_platform] += 1
        for identity in {source_key(manifest_source), str(manifest_source.get("source_id") or "")}:
            if identity:
                manifest_offsets_by_id[identity] = offset
        manifest_url = canonical_url_key(manifest_source.get("url"))
        if manifest_url:
            manifest_offsets_by_url[manifest_url] = offset
    report_by_url = {
        canonical_url_key(row.get("url")): row
        for row in report_index.values()
        if canonical_url_key(row.get("url"))
    }
    prior_by_id: dict[str, dict[str, Any]] = {}
    prior_by_url: dict[str, dict[str, Any]] = {}
    for prior_row in (prior_matrix or {}).get("sources", []):
        for identity in {
            str(prior_row.get("candidate_id") or ""),
            str(prior_row.get("source_id") or ""),
            source_key(prior_row),
        }:
            if identity:
                prior_by_id[identity] = prior_row
        prior_url = canonical_url_key(prior_row.get("url"))
        if prior_url:
            prior_by_url[prior_url] = prior_row
    pub_state, pub_evidence = publication_evidence(conductor)
    rows: list[dict[str, Any]] = []
    row_manifest_offsets: dict[str, int] = {}
    seen: set[str] = set()
    for source in readiness_rows:
        key = source_key(source)
        if not key or key in seen:
            raise ValueError(f"duplicate or missing source identity: {key!r}")
        seen.add(key)
        url_keys = alternative_capture_url_keys(source)
        manifest_row = manifest_by_id.get(key) or next(
            (manifest_by_url[url_key] for url_key in url_keys if url_key in manifest_by_url),
            {},
        )
        registered = bool(manifest_row)
        manifest_key = str(manifest_row.get("source_id") or source_key(manifest_row))
        manifest_offset = manifest_offsets_by_id.get(manifest_key)
        if manifest_offset is None:
            manifest_offset = next(
                (manifest_offsets_by_url[url_key] for url_key in url_keys if url_key in manifest_offsets_by_url),
                0,
            )
        merged = {**manifest_row, **source, "_manifest_offset": manifest_offset}
        evidence = report_index.get(key) or next(
            (report_by_url[url_key] for url_key in url_keys if url_key in report_by_url),
            {},
        )
        normalized_count = max(normalized[key], normalized[manifest_key])
        state, blocker = classify_state(merged, registered, evidence, normalized_count)
        prior = (
            prior_by_id.get(key)
            or prior_by_id.get(manifest_key)
            or next((prior_by_url[url_key] for url_key in url_keys if url_key in prior_by_url), {})
        )
        prior_state = str(prior.get("completion_state") or "")
        current_status = str(evidence.get("status") or "")
        reopens_external = current_status in SUCCESS_STATUSES | {"seed_present", "public_fallback_available"}
        if prior_state == "archived" and state != "archived":
            state = "archived"
            blocker = str(prior.get("blocker_class") or "archive_evidence")
        elif prior_state in COMPLETE_STATES and state not in COMPLETE_STATES and not reopens_external:
            state = prior_state
            blocker = str(prior.get("blocker_class") or "preserved_terminal_evidence")
        if state not in LIFECYCLE_STATES:
            raise ValueError(f"invalid lifecycle state for {key}: {state}")
        action, acceptance = next_action(merged, state)
        platform = str(merged.get("platform") or merged.get("source_type") or "unknown")
        archive_evidence = [str(evidence.get("evidence_report") or "")] if evidence else []
        archive_evidence = sorted({
            item for item in [*prior.get("archive_evidence", []), *archive_evidence] if item
        })
        record_count = max(int(prior.get("record_count") or 0), normalized_count)
        row_publication_evidence = sorted({
            item for item in [*prior.get("publication_evidence", []), *(pub_evidence if state == "archived" else [])] if item
        })
        row = {
            "source_id": key,
            "candidate_id": str(merged.get("candidate_id") or ""),
            "agency_id": str(merged.get("agency_id") or ""),
            "agency_name": str(merged.get("agency_name") or ""),
            "source_type": str(merged.get("source_type") or "unknown"),
            "platform": platform,
            "url": str(merged.get("url") or ""),
            "registry_state": "registered" if registered else "candidate",
            "capture_adapter": ADAPTERS.get(platform, "adapter_review_required"),
            "capture_workflow": WORKFLOWS.get(platform, ""),
            "auth": str(merged.get("auth") or "unknown"),
            "historical_capture_state": "evidence_present" if state == "archived" else "no_archive_evidence",
            "ongoing_capture_state": "scheduled" if platform in WORKFLOWS and registered else "not_scheduled",
            "publication_state": pub_state if state == "archived" else "not_applicable_until_archived",
            "record_count": record_count,
            "archive_evidence": archive_evidence,
            "publication_evidence": row_publication_evidence,
            "latest_status": str(evidence.get("status") or ""),
            "completion_state": state,
            "complete": state in COMPLETE_STATES,
            "blocker_class": blocker,
            "next_action": action,
            "acceptance_condition": acceptance,
            "retry_count": 0,
            "updated_at": now_iso(),
        }
        rows.append(row)
        row_manifest_offsets[key] = manifest_offset
    if len(rows) != int(readiness.get("total_sources") or len(readiness_rows)):
        raise ValueError("completion matrix does not reconcile to readiness total")
    state_counts = Counter(row["completion_state"] for row in rows)
    platform_counts = Counter(row["platform"] for row in rows)
    registered_count = sum(row["registry_state"] == "registered" for row in rows)
    queue_rows = [row for row in rows if not row["complete"]]
    queue_rows.sort(key=lambda row: (PRIORITY.get(row["platform"], 100), row["agency_id"], row["source_id"]))
    queue_items: list[dict[str, Any]] = []
    queue_platform_offsets: Counter[str] = Counter()
    for rank, row in enumerate(queue_rows, start=1):
        platform_queue_offset = queue_platform_offsets[row["platform"]]
        queue_platform_offsets[row["platform"]] += 1
        dispatch_row = {
            **row,
            "_manifest_offset": row_manifest_offsets.get(row["source_id"], 0),
            "_queue_offset": platform_queue_offset,
        }
        queue_items.append({
            "rank": rank, "source_id": row["source_id"], "agency_id": row["agency_id"],
            "platform": row["platform"], "url": row["url"], "completion_state": row["completion_state"],
            "next_action": row["next_action"], "dispatch": dispatch_for(dispatch_row, row["completion_state"]),
            "expected_evidence": row["archive_evidence"] or ["conductor/archive_completion_matrix.json"],
            "acceptance_condition": row["acceptance_condition"],
        })
    generated_at = now_iso()
    matrix = {
        "schema_version": 1, "track_id": TRACK_ID, "generated_at": generated_at,
        "description": "Canonical completion state for every identified NZ government archive candidate.",
        "summary": {
            "total_candidates": len(rows), "registered_sources": registered_count,
            "archived_sources": state_counts["archived"],
            "terminal_evidence_sources": sum(state_counts[state] for state in COMPLETE_STATES if state != "archived"),
            "complete_sources": sum(row["complete"] for row in rows),
            "incomplete_actionable_sources": len(queue_rows),
            "external_access_sources": state_counts["terminal_external_access"],
            "automation_faults": state_counts["automation_fault"],
            "completion_percent": round(100 * sum(row["complete"] for row in rows) / len(rows), 2) if rows else 100.0,
            "state_counts": dict(sorted(state_counts.items())),
            "platform_counts": dict(sorted(platform_counts.items())),
        },
        "sources": rows,
    }
    queue = {
        "schema_version": 1, "track_id": TRACK_ID, "generated_at": generated_at,
        "summary": {"queue_count": len(queue_items), "dispatchable_count": sum(item["dispatch"]["dispatchable"] for item in queue_items)},
        "items": queue_items,
    }
    return matrix, queue


def validate_matrix(matrix: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    rows = matrix.get("sources", [])
    ids = [row.get("source_id") for row in rows]
    if len(ids) != len(set(ids)):
        errors.append("duplicate source IDs")
    if len(rows) != matrix.get("summary", {}).get("total_candidates"):
        errors.append("summary total does not match row count")
    for row in rows:
        state = row.get("completion_state")
        if state not in LIFECYCLE_STATES:
            errors.append(f"{row.get('source_id')}: invalid lifecycle state {state}")
        if row.get("complete") != (state in COMPLETE_STATES):
            errors.append(f"{row.get('source_id')}: completion flag contradicts state")
        if state == "archived" and not row.get("archive_evidence") and not row.get("record_count"):
            errors.append(f"{row.get('source_id')}: archived without evidence")
        if state == "archived" and not row.get("publication_evidence"):
            errors.append(f"{row.get('source_id')}: archived without publication evidence")
    return errors


def write_markdown(path: Path, matrix: dict[str, Any], queue: dict[str, Any]) -> None:
    summary = matrix["summary"]
    lines = [
        "# NZ Government Archive Completion Matrix", "", f"Generated: {matrix['generated_at']}", "",
        "## Completion", "", "| Metric | Count |", "| --- | ---: |",
        f"| Total candidates | {summary['total_candidates']} |",
        f"| Registered sources | {summary['registered_sources']} |",
        f"| Archived sources | {summary['archived_sources']} |",
        f"| Terminal evidence sources | {summary['terminal_evidence_sources']} |",
        f"| Incomplete actionable sources | {summary['incomplete_actionable_sources']} |",
        f"| Automation faults | {summary['automation_faults']} |",
        f"| Completion | {summary['completion_percent']}% |", "", "## Lifecycle states", "",
        "| State | Count |", "| --- | ---: |",
    ]
    for state, count in summary["state_counts"].items():
        lines.append(f"| `{state}` | {count} |")
    lines.extend(["", "## Next work", "", "| Rank | Platform | Agency | Source | Action |", "| ---: | --- | --- | --- | --- |"])
    for item in queue["items"][:100]:
        lines.append(f"| {item['rank']} | `{item['platform']}` | `{item['agency_id']}` | `{item['source_id']}` | `{item['next_action']}` |")
    lines.extend(["", "The full deterministic queue is in `conductor/archive_completion_work_queue.json`.", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--readiness", type=Path, default=ROOT / "conductor/govt_archive_readiness_matrix.json")
    parser.add_argument("--manifest", type=Path, default=ROOT / "conductor/govt_archive_source_manifest.json")
    parser.add_argument("--conductor", type=Path, default=ROOT / "conductor")
    parser.add_argument("--normalized-root", type=Path, default=ROOT / "historical_archive_normalized")
    parser.add_argument("--output", type=Path, default=ROOT / "conductor/archive_completion_matrix.json")
    parser.add_argument("--markdown", type=Path, default=ROOT / "conductor/archive_completion_matrix.md")
    parser.add_argument("--queue", type=Path, default=ROOT / "conductor/archive_completion_work_queue.json")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    if args.validate_only:
        errors = validate_matrix(load_json(args.output, {}))
        if errors:
            raise SystemExit("\n".join(errors))
        print(f"Archive completion matrix valid: {args.output}")
        return
    prior_matrix = load_json(args.output, {})
    matrix, queue = build_completion_matrix(
        load_json(args.readiness, {}), load_json(args.manifest, {}),
        build_report_index(args.conductor), normalized_counts(args.normalized_root), args.conductor,
        prior_matrix=prior_matrix,
    )
    errors = validate_matrix(matrix)
    if errors:
        raise SystemExit("\n".join(errors))
    args.output.write_text(json.dumps(matrix, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.queue.write_text(json.dumps(queue, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(args.markdown, matrix, queue)
    print(f"Archive completion matrix wrote {len(matrix['sources'])} rows and {len(queue['items'])} queue items.")


if __name__ == "__main__":
    main()
