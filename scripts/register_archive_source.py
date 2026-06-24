import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_MANIFEST = Path("conductor/govt_archive_source_manifest.json")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "generated_at": now_iso(),
            "description": "Archive onboarding manifest for government public communication sources.",
            "summary": {"total_sources": 0, "archive_status_counts": {}},
            "sources": [],
        }
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    counts: dict[str, int] = {}
    for source in manifest["sources"]:
        status = source.get("archive_status", "unknown")
        counts[status] = counts.get(status, 0) + 1
    manifest["generated_at"] = now_iso()
    manifest["summary"] = {
        "total_sources": len(manifest["sources"]),
        "archive_status_counts": dict(sorted(counts.items())),
    }
    manifest["sources"] = sorted(
        manifest["sources"],
        key=lambda row: (row.get("agency_id", ""), row.get("platform", ""), row.get("url", "")),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def upsert_source(manifest: dict[str, Any], source: dict[str, Any]) -> str:
    for index, existing in enumerate(manifest["sources"]):
        if existing.get("source_id") == source["source_id"] or (
            existing.get("agency_id") == source["agency_id"]
            and existing.get("platform") == source["platform"]
            and existing.get("url") == source["url"]
        ):
            merged = {**existing, **source, "updated_at": now_iso()}
            manifest["sources"][index] = merged
            return "updated"
    source["created_at"] = now_iso()
    manifest["sources"].append(source)
    return "added"


def main() -> None:
    parser = argparse.ArgumentParser(description="Register or update one government archive source.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--agency-id", required=True)
    parser.add_argument("--agency-name", default="")
    parser.add_argument("--source-type", required=True)
    parser.add_argument("--platform", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--account", default="")
    parser.add_argument("--feasibility", default="review_required")
    parser.add_argument("--archive-status", default="candidate")
    parser.add_argument("--access-method", default="review_required")
    parser.add_argument("--auth", default="review_required")
    parser.add_argument("--origin", default="manual.registration")
    parser.add_argument("--notes", default="")
    args = parser.parse_args()

    manifest = load_manifest(args.manifest)
    outcome = upsert_source(
        manifest,
        {
            "source_id": args.source_id,
            "agency_id": args.agency_id,
            "agency_name": args.agency_name,
            "source_type": args.source_type,
            "platform": args.platform,
            "url": args.url,
            "account": args.account,
            "feasibility": args.feasibility,
            "archive_status": args.archive_status,
            "access_method": args.access_method,
            "auth": args.auth,
            "origin": args.origin,
            "notes": args.notes,
        },
    )
    write_manifest(args.manifest, manifest)
    print(f"{outcome} {args.source_id}")


if __name__ == "__main__":
    main()
