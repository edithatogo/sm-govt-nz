import argparse
from collections import defaultdict
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Protocol

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.bluesky import BlueskyApiClient


class PostLookupClient(Protocol):
    def fetch_posts(self, uris: list[str]) -> list[Mapping[str, Any]]:
        """Return public post records for AT Protocol post URIs."""

    def fetch_author_feed(
        self, actor: str, *, limit: int = 100
    ) -> list[Mapping[str, Any]]:
        """Return public feed records for one mirror account."""


def verify_archive_mirror_posts(
    *,
    state_path: str | Path = "conductor/archive_mirror_state.json",
    target: str = "bluesky",
    limit: int = 5,
    client: PostLookupClient | None = None,
) -> dict[str, Any]:
    deliveries = _load_deliveries(Path(state_path), target=target)
    sampled = deliveries[-limit:] if limit > 0 else deliveries
    uris = [delivery["detail"] for delivery in sampled if delivery["detail"].startswith("at://")]
    posts_by_uri = {
        str(post.get("uri") or ""): post
        for post in (client or BlueskyApiClient()).fetch_posts(uris)
    }
    results: list[dict[str, Any]] = []
    for delivery in sampled:
        uri = delivery["detail"]
        post = posts_by_uri.get(uri)
        results.append(
            {
                "record_id": delivery["record_id"],
                "uri": uri,
                "mirror_url": delivery["mirror_url"],
                "valid": post is not None,
            }
        )

    failures = [result for result in results if not result["valid"]]
    return {
        "checked": len(results),
        "failures": failures,
        "target": target,
        "valid": not failures,
    }


def reconcile_programme_audit(
    *,
    registry_path: str | Path,
    mirror_id: str,
    audit_paths: list[str | Path],
    client: PostLookupClient | None = None,
) -> dict[str, Any]:
    """Build a non-destructive cleanup and reconciliation report."""
    registry = json.loads(Path(registry_path).read_text(encoding="utf-8"))
    account = next(
        row for row in registry.get("mirrors", []) if row.get("mirror_id") == mirror_id
    )
    audit_rows = _load_audit_rows(audit_paths, mirror_id)
    known_uris = sorted(
        {
            str(row.get("uri") or "")
            for row in audit_rows
            if str(row.get("uri") or "").startswith("at://")
        }
    )
    lookup = client or BlueskyApiClient()
    visible_posts = lookup.fetch_posts(known_uris) if known_uris else []
    visible_uris = {
        str(post.get("uri") or "") for post in visible_posts if post.get("uri")
    }
    feed_posts = _author_feed_posts(lookup, str(account.get("handle") or ""))
    audit_uri_set = set(known_uris)

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in audit_rows:
        uri = str(row.get("uri") or "")
        if uri:
            grouped[
                (
                    str(row.get("record_id") or ""),
                    str(row.get("rendered_hash") or ""),
                )
            ].append(row)
    duplicates = []
    for (record_id, rendered_hash), rows in sorted(grouped.items()):
        rows_by_uri = {
            str(row.get("uri") or ""): row
            for row in rows
            if str(row.get("uri") or "")
        }
        if len(rows_by_uri) < 2:
            continue
        keeper_uri = max(
            rows_by_uri,
            key=lambda uri: (
                rows_by_uri[uri].get("reconciled") is True,
                str(rows_by_uri[uri].get("status") or "") == "posted",
                str(rows_by_uri[uri].get("attempted_at") or ""),
                uri,
            ),
        )
        duplicates.append(
            {
                "record_id": record_id,
                "rendered_hash": rendered_hash,
                "keeper_uri": keeper_uri,
                "duplicate_uris": sorted(set(rows_by_uri) - {keeper_uri}),
                "uris": sorted(rows_by_uri),
            }
        )
    allowed_source_ids = {str(value) for value in account.get("source_ids", [])}
    classified_rows = [
        (row, _effective_source_id(row, allowed_source_ids)) for row in audit_rows
    ]
    excluded_sources = [
        {
            "record_id": str(row.get("record_id") or ""),
            "source_id": source_id,
            "uri": str(row.get("uri") or ""),
            "reason": "source_id_not_allowed",
        }
        for row, source_id in classified_rows
        if source_id not in allowed_source_ids
    ]
    deleted_or_missing = [
        {"uri": uri, "reason": "not_visible_via_public_api"}
        for uri in known_uris
        if uri not in visible_uris
    ]
    activation = str(account.get("activated_at") or "")
    post_activation_feed_uris = {
        uri
        for uri, created_at in feed_posts.items()
        if _is_at_or_after_activation(created_at, activation)
    }
    missing_audit = [
        {"uri": uri, "reason": "public_post_missing_audit"}
        for uri in sorted(post_activation_feed_uris - audit_uri_set)
    ]
    pre_activation_posts_ignored = sorted(
        set(feed_posts) - post_activation_feed_uris
    )

    actions: dict[str, set[str]] = defaultdict(set)
    for duplicate in duplicates:
        for uri in duplicate["duplicate_uris"]:
            actions[uri].add("duplicate")
    for excluded in excluded_sources:
        uri = excluded["uri"]
        if uri.startswith("at://"):
            actions[uri].add("excluded_source")
    cleanup_candidates = [
        {
            "uri": uri,
            "reasons": sorted(reasons),
            "requires_exact_uri_approval": True,
            "action": "review_for_deletion",
        }
        for uri, reasons in sorted(actions.items())
    ]
    return {
        "schema_version": 1,
        "mirror_id": mirror_id,
        "checked_audit_rows": len(audit_rows),
        "visible_known_posts": len(visible_uris),
        "duplicates": duplicates,
        "excluded_sources": excluded_sources,
        "deleted_or_missing": deleted_or_missing,
        "missing_audit": missing_audit,
        "pre_activation_posts_ignored": pre_activation_posts_ignored,
        "cleanup_approval_packet": {
            "destructive_action_performed": False,
            "requires_exact_uri_approval": True,
            "candidates": cleanup_candidates,
        },
        "valid": not (
            duplicates or excluded_sources or deleted_or_missing or missing_audit
        ),
    }


def _load_audit_rows(
    audit_paths: list[str | Path], mirror_id: str
) -> list[dict[str, Any]]:
    paths: list[Path] = []
    for value in audit_paths:
        path = Path(value)
        paths.extend(sorted(path.glob("*.jsonl")) if path.is_dir() else [path])
    rows = []
    for path in paths:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("mirror_id") == mirror_id:
                rows.append(row)
    return rows


def _effective_source_id(
    row: Mapping[str, Any], allowed_source_ids: set[str]
) -> str:
    source_id = str(row.get("source_id") or "")
    if source_id:
        return source_id
    record_namespace = str(row.get("record_id") or "").partition(":")[0]
    platform = record_namespace.partition("_")[0].casefold()
    if not platform:
        return ""
    candidates = [
        candidate
        for candidate in allowed_source_ids
        if f"-{platform}-" in f"-{candidate.casefold()}-"
    ]
    return candidates[0] if len(candidates) == 1 else ""


def _author_feed_posts(client: PostLookupClient, handle: str) -> dict[str, str]:
    if not handle or not hasattr(client, "fetch_author_feed"):
        return {}
    try:
        feed = client.fetch_author_feed(handle, limit=100)
    except Exception:
        return {}
    posts = {}
    for item in feed:
        post = item.get("post") if isinstance(item.get("post"), Mapping) else item
        uri = str(post.get("uri") or "")
        if uri:
            record = post.get("record")
            created_at = (
                str(record.get("createdAt") or "")
                if isinstance(record, Mapping)
                else ""
            )
            posts[uri] = created_at or str(post.get("indexedAt") or "")
    return posts


def _is_at_or_after_activation(created_at: str, activated_at: str) -> bool:
    if not activated_at or not created_at:
        return True
    try:
        created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        activated = datetime.fromisoformat(activated_at.replace("Z", "+00:00"))
    except ValueError:
        return True
    if created.tzinfo is None or activated.tzinfo is None:
        return True
    return created >= activated

def _load_deliveries(state_path: Path, *, target: str) -> list[dict[str, str]]:
    if not state_path.exists():
        return []
    data = json.loads(state_path.read_text(encoding="utf-8"))
    posted_records = data.get("posted_records", {})
    if not isinstance(posted_records, dict):
        return []
    target_records = posted_records.get(target, {})
    if not isinstance(target_records, dict):
        return []

    deliveries: list[dict[str, str]] = []
    for source_deliveries in target_records.values():
        if not isinstance(source_deliveries, list):
            continue
        for delivery in source_deliveries:
            if not isinstance(delivery, dict):
                continue
            detail = str(delivery.get("detail") or "")
            if not detail.startswith("at://"):
                continue
            deliveries.append(
                {
                    "detail": detail,
                    "mirror_url": str(delivery.get("mirror_url") or ""),
                    "record_id": str(delivery.get("record_id") or ""),
                }
            )
    return deliveries


def result_exit_code(
    result: Mapping[str, Any],
    *,
    report_only: bool = False,
    reconciliation: bool = False,
) -> int:
    """Keep strict verification by default while allowing evidence-only reports."""
    if report_only and not reconciliation:
        raise ValueError("report-only mode requires programme reconciliation")
    return 0 if report_only or result["valid"] else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify sampled archive mirror posts exist.")
    parser.add_argument("--state-path", default="conductor/archive_mirror_state.json")
    parser.add_argument("--target", default="bluesky")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--reconcile-programme", action="store_true")
    parser.add_argument("--registry", default="config/mirror_accounts.json")
    parser.add_argument("--mirror-id", default="")
    parser.add_argument(
        "--audit-path",
        action="append",
        default=[],
    )
    parser.add_argument("--output", default="")
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Write and print findings without treating reconciliation findings as an execution fault.",
    )
    args = parser.parse_args()

    if args.reconcile_programme:
        if not args.mirror_id or not args.output:
            raise SystemExit("--mirror-id and --output are required.")
        result = reconcile_programme_audit(
            registry_path=args.registry,
            mirror_id=args.mirror_id,
            audit_paths=args.audit_path
            or [
                "conductor/bluesky_mirror_post_audit.jsonl",
                "conductor/bluesky_mirror_audit",
            ],
        )
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    else:
        result = verify_archive_mirror_posts(
            state_path=args.state_path,
            target=args.target,
            limit=args.limit,
        )
    if args.json or args.reconcile_programme or not result["valid"]:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"Verified {result['checked']} archive mirror posts for {result['target']}.")
    raise SystemExit(
        result_exit_code(
            result,
            report_only=args.report_only,
            reconciliation=args.reconcile_programme,
        )
    )


if __name__ == "__main__":
    main()
