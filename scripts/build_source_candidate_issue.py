import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


REVIEW_SOURCE_TYPES = {
    "social_profile",
    "rss_feed",
    "json_feed",
    "websub_hub",
    "activitypub_profile",
    "api_endpoint",
    "microformat_feed",
    "newsletter",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def review_candidates(report: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = []
    for item in report.get("candidates", []):
        if item.get("source_type") not in REVIEW_SOURCE_TYPES:
            continue
        if item.get("origin") == "registry.social_profiles":
            continue
        if item.get("archive_status") in {"blocked", "degraded"}:
            continue
        candidates.append(item)
    return sorted(
        candidates,
        key=lambda row: (
            -float(row.get("confidence_score", 0)),
            str(row.get("platform", "")),
            str(row.get("agency_id", "")),
            str(row.get("url", "")),
        ),
    )


def markdown_table(candidates: list[dict[str, Any]], limit: int) -> str:
    rows = [
        "| Confidence | Platform | Type | Agency | URL | Origin |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in candidates[:limit]:
        rows.append(
            "| {confidence} | {platform} | {source_type} | {agency} | {url} | {origin} |".format(
                confidence=item.get("confidence_score", ""),
                platform=item.get("platform", ""),
                source_type=item.get("source_type", ""),
                agency=item.get("agency_id", ""),
                url=item.get("url", ""),
                origin=item.get("origin", ""),
            )
        )
    return "\n".join(rows)


def build_body(report: dict[str, Any], candidates: list[dict[str, Any]], limit: int) -> str:
    counts = Counter(item.get("platform", "unknown") for item in candidates)
    lines = [
        "# Source discovery candidates need review",
        "",
        f"Generated: {report.get('generated_at', '')}",
        "",
        "The discovery workflow found reviewable public-source candidates that are not yet confirmed registry social profiles.",
        "",
        "## Candidate counts by platform",
        "",
    ]
    for platform, count in sorted(counts.items()):
        lines.append(f"- `{platform}`: {count}")
    lines.extend(
        [
            "",
            "## Top candidates",
            "",
            markdown_table(candidates, limit),
            "",
            "## Review checklist",
            "",
            "- Confirm the source belongs to the named NZ government agency.",
            "- Prefer official site links, verified profiles, WebFinger, rel=me, or agency registry evidence.",
            "- Reject fan, parody, unofficial, stale, or unrelated accounts.",
            "- For feed/API candidates, confirm terms, stability, and whether scheduled polling or realtime push is appropriate.",
            "- Once accepted, add or regenerate the per-agency config so archive workflows include the source.",
        ]
    )
    if len(candidates) > limit:
        lines.append("")
        lines.append(f"Showing {limit} of {len(candidates)} candidates. See `conductor/govt_source_candidate_report.json` for all records.")
    return "\n".join(lines) + "\n"


def write_github_output(path: Path, has_candidates: bool, count: int, title: str) -> None:
    output = Path(str(path))
    if not output:
        return
    with output.open("a", encoding="utf-8") as handle:
        handle.write(f"has_candidates={'true' if has_candidates else 'false'}\n")
        handle.write(f"candidate_count={count}\n")
        handle.write(f"title={title}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a GitHub issue body for source discovery candidates.")
    parser.add_argument("--report", type=Path, default=Path("conductor/govt_source_candidate_report.json"))
    parser.add_argument("--body-output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=40)
    args = parser.parse_args()

    report = load_json(args.report)
    candidates = review_candidates(report)
    title = "Review newly discovered NZ government public-source candidates"
    args.body_output.parent.mkdir(parents=True, exist_ok=True)
    args.body_output.write_text(build_body(report, candidates, args.limit), encoding="utf-8")
    github_output = Path(__import__("os").environ.get("GITHUB_OUTPUT", ""))
    if github_output:
        write_github_output(github_output, bool(candidates), len(candidates), title)
    print(f"Reviewable source candidates: {len(candidates)}")


if __name__ == "__main__":
    main()
