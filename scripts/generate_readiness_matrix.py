"""Generate the Government Archive Readiness Matrix."""
from __future__ import annotations
import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

READINESS_STATES = [
    "discovered", "registered", "resolver_ok", "capture_ok",
    "normalized_ok", "published_ok", "blocked_credential",
    "blocked_legal", "blocked_technical", "stale", "retired",
]
SOURCE_TYPES = [
    "website_page", "rss", "bluesky", "youtube", "newsletter",
    "facebook", "instagram", "medium", "substack", "threads", "linkedin", "x",
]
NON_CREDENTIAL_TYPES = {"website_page", "rss", "bluesky", "youtube", "newsletter", "medium", "substack"}
CREDENTIAL_GATED_TYPES = {"facebook", "instagram", "threads", "linkedin", "x"}
ARCHIVE_ONLY_PLATFORMS = {"linkedin", "newsletter", "rss", "website_page", "youtube", "medium", "substack"}
MIRROR_CAPABLE_PLATFORMS = {"bluesky", "facebook", "instagram", "threads", "x"}
DEPENDENCY_GATES = {
    "registry": ["discovered", "registered"],
    "resolver": ["registered", "resolver_ok"],
    "capture": ["resolver_ok", "capture_ok"],
    "normalize": ["capture_ok", "normalized_ok"],
    "publish": ["normalized_ok", "published_ok"],
}

def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def load_json(path: Path) -> dict[str, Any] | list[Any] | None:
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as f:
        return json.load(f)

def map_manifest_status_to_readiness(archive_status: str, auth: str, platform: str, feasibility: str) -> str:
    status_map = {
        "ready": "resolver_ok",
        "candidate": "discovered",
        "manual_seed": "registered",
        "degraded": "blocked_technical",
    }
    readiness = status_map.get(archive_status, "discovered")
    if platform in CREDENTIAL_GATED_TYPES and readiness in ("resolver_ok", "capture_ok"):
        if "operator_or_app" in auth or "operator_authorized" in auth:
            readiness = "blocked_credential"
    if feasibility == "low" and readiness in ("resolver_ok",):
        readiness = "blocked_technical"
    return readiness

def map_candidate_status_to_readiness(status: str, feasibility: str, platform: str) -> str:
    if platform in CREDENTIAL_GATED_TYPES:
        return "blocked_credential"
    status_map = {"discovered": "discovered", "needs_probe": "discovered", "active": "registered", "would_capture": "resolver_ok"}
    base = status_map.get(status, "discovered")
    if feasibility == "low" and base == "resolver_ok":
        return "blocked_technical"
    return base

def build_readiness_rows(manifest, candidate_report, source_health):
    rows = []
    seen_ids = set()
    if manifest and "sources" in manifest:
        for src in manifest["sources"]:
            source_id = src.get("source_id", "")
            if source_id in seen_ids:
                continue
            seen_ids.add(source_id)
            readiness = map_manifest_status_to_readiness(src.get("archive_status", "unknown"), src.get("auth", "unknown"), src.get("platform", "unknown"), src.get("feasibility", "medium"))
            rows.append({"source_id": source_id, "agency_id": src.get("agency_id", ""), "agency_name": src.get("agency_name", ""), "source_type": src.get("source_type", "unknown"), "platform": src.get("platform", "unknown"), "url": src.get("url", ""), "readiness": readiness, "feasibility": src.get("feasibility", "medium"), "auth": src.get("auth", "unknown"), "origin": src.get("origin", ""), "notes": src.get("notes", "")})
    if candidate_report and "results" in candidate_report:
        for cand in candidate_report["results"]:
            source_id = cand.get("source_id", cand.get("candidate_id", ""))
            if source_id in seen_ids:
                continue
            seen_ids.add(source_id)
            readiness = map_candidate_status_to_readiness(cand.get("status", "discovered"), cand.get("feasibility", "medium"), cand.get("platform", "unknown"))
            rows.append({"source_id": source_id, "agency_id": cand.get("agency_id", ""), "agency_name": cand.get("agency_name", ""), "source_type": cand.get("source_type", "unknown"), "platform": cand.get("platform", "unknown"), "url": cand.get("url", ""), "readiness": readiness, "feasibility": cand.get("feasibility", "medium"), "auth": "unknown", "origin": cand.get("origin", ""), "notes": cand.get("policy_notes", "")})
    return rows

def classify_archive_mode(platform: str, readiness: str) -> str:
    if platform in ARCHIVE_ONLY_PLATFORMS:
        return "archive_only"
    if platform in MIRROR_CAPABLE_PLATFORMS:
        if readiness in ("published_ok", "normalized_ok", "capture_ok"):
            return "mirror_capable"
        return "mirror_pending"
    return "unknown"

def compute_dependency_gates(rows):
    total = len(rows)
    readiness_counts = Counter(row["readiness"] for row in rows)
    gates = {}
    for gate_name, (lower, upper) in DEPENDENCY_GATES.items():
        passing = readiness_counts.get(upper, 0)
        pending = readiness_counts.get(lower, 0)
        blocked = total - passing - pending
        gates[gate_name] = {"pass": passing, "pending": pending, "blocked": blocked, "total": total}
    return gates

def build_summary(rows):
    readiness_counts = Counter()
    platform_counts = Counter()
    source_type_counts = Counter()
    archive_mode_counts = Counter()
    credential_blocked = 0
    capturable_no_creds = 0
    for row in rows:
        readiness_counts[row["readiness"]] += 1
        platform_counts[row["platform"]] += 1
        source_type_counts[row["source_type"]] += 1
        mode = classify_archive_mode(row["platform"], row["readiness"])
        archive_mode_counts[mode] += 1
        if row["readiness"] == "blocked_credential":
            credential_blocked += 1
        if row["readiness"] in ("resolver_ok", "capture_ok", "normalized_ok", "published_ok"):
            if row["platform"] in NON_CREDENTIAL_TYPES:
                capturable_no_creds += 1
    return {"total_sources": len(rows), "readiness_counts": dict(readiness_counts.most_common()), "platform_counts": dict(platform_counts.most_common()), "source_type_counts": dict(source_type_counts.most_common()), "archive_mode_counts": dict(archive_mode_counts.most_common()), "capturable_without_credentials": capturable_no_creds, "credential_gated_blocked": credential_blocked}

def generate_markdown(rows, summary):
    lines = ["# Government Archive Readiness Matrix", "", f"Generated: {now_iso()}", f"Total sources: {summary['total_sources']}", "", "## Summary", "", "| Metric | Count |", "|--------|-------|"]
    for metric, count in sorted(summary.items()):
        if isinstance(count, int):
            lines.append(f"| {metric.replace('_', ' ').title()} | {count} |")
        elif isinstance(count, dict):
            lines.append(f"| {metric.replace('_', ' ').title()} | See below |")
    lines.extend(["", "### Readiness Distribution", "", "| State | Count |", "|-------|-------|"])
    for state, count in summary.get("readiness_counts", {}).items():
        lines.append(f"| {state} | {count} |")
    lines.extend(["", "### Platform Distribution", "", "| Platform | Count |", "|----------|-------|"])
    for platform, count in summary.get("platform_counts", {}).items():
        lines.append(f"| {platform} | {count} |")
    lines.extend(["", "### Archive Mode Distribution", "", "| Mode | Count |", "|------|-------|"])
    for mode, count in summary.get("archive_mode_counts", {}).items():
        lines.append(f"| {mode} | {count} |")
    lines.extend(["", "## Agency Breakdown", "", "| Agency | Total | Discovered | Registered | Resolver OK | Capture OK | Published | Blocked Credential | Blocked Technical |", "|--------|-------|------------|------------|-------------|------------|-----------|-------------------|--------------------|"])
    agency_groups = {}
    for row in rows:
        aid = row["agency_id"]
        if aid not in agency_groups:
            agency_groups[aid] = {"name": row["agency_name"], "total": 0, "discovered": 0, "registered": 0, "resolver_ok": 0, "capture_ok": 0, "published_ok": 0, "blocked_credential": 0, "blocked_technical": 0}
        g = agency_groups[aid]
        g["total"] += 1
        state = row["readiness"]
        if state in g:
            g[state] += 1
    for aid in sorted(agency_groups):
        g = agency_groups[aid]
        lines.append(f"| {g['name']} | {g['total']} | {g['discovered']} | {g['registered']} | {g['resolver_ok']} | {g['capture_ok']} | {g['published_ok']} | {g['blocked_credential']} | {g['blocked_technical']} |")
    return "\n".join(lines)

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Government Archive Readiness Matrix")
    parser.add_argument("--manifest", type=Path, default=ROOT / "conductor" / "govt_archive_source_manifest.json")
    parser.add_argument("--candidates", type=Path, default=ROOT / "conductor" / "govt_source_candidate_report.json")
    parser.add_argument("--health", type=Path, default=ROOT / "conductor" / "archive_source_health.json")
    parser.add_argument("--output", type=Path, default=ROOT / "conductor" / "govt_archive_readiness_matrix.json")
    parser.add_argument("--markdown", type=Path, default=ROOT / "conductor" / "govt_archive_readiness_matrix.md")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    manifest = load_json(args.manifest)
    candidate_report = load_json(args.candidates)
    source_health = load_json(args.health)
    if not manifest and not candidate_report:
        print("No source data found.")
        return
    rows = build_readiness_rows(manifest if isinstance(manifest, dict) else None, candidate_report if isinstance(candidate_report, dict) else None, source_health if isinstance(source_health, dict) else None)
    summary = build_summary(rows)
    gates = compute_dependency_gates(rows)
    output = {"generated_at": now_iso(), "description": "Government archive readiness matrix with dependency sequencing", "track_id": "govt_archive_readiness_matrix_20260625", "total_sources": len(rows), "dependency_gates": gates, "summary": summary, "sources": rows}
    if args.dry_run:
        print(f"Dry run: {len(rows)} rows")
        print(json.dumps(summary, indent=2))
        print(json.dumps(gates, indent=2))
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    print(f"Written: {args.output} ({len(rows)} rows)")
    md = generate_markdown(rows, summary)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text(md, encoding="utf-8")
    print(f"Written: {args.markdown}")
    for gate, info in gates.items():
        print(f"Gate {gate}: {info['pass']} pass / {info['pending']} pending / {info['blocked']} blocked / {info['total']} total")

if __name__ == "__main__":
    main()
