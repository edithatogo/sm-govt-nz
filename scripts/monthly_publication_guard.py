import argparse
import datetime as dt
import json
import os
from pathlib import Path
from typing import Any


def already_published_this_release(status_path: Path, release_version: str) -> bool:
    if not status_path.exists():
        return False
    try:
        status = json.loads(status_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    if str(status.get("release_version") or "") != release_version:
        return False
    if status.get("mode") != "published":
        return False
    published_targets = [
        status.get("hugging_face"),
        status.get("zenodo"),
        status.get("osf"),
    ]
    if any(
        isinstance(value, dict) and value.get("status") == "published"
        for value in published_targets
    ):
        return True
    results = status.get("publication_results", {})
    return bool(results)


def release_version_in_ledger(ledger_path: Path, release_version: str) -> bool:
    if not ledger_path.exists():
        return False
    try:
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    releases = ledger.get("releases", [])
    if not isinstance(releases, list):
        return False
    for release in releases:
        if not isinstance(release, dict):
            continue
        if str(release.get("release_version") or "") != release_version:
            continue
        if release.get("mode") == "published":
            return True
        if release.get("hugging_face") == "published":
            return True
        if release.get("zenodo") == "published":
            return True
        if release.get("osf") == "published":
            return True
    return False


def write_github_output(values: dict[str, Any]) -> None:
    output_path = os.getenv("GITHUB_OUTPUT")
    lines = [f"{key}={value}" for key, value in values.items()]
    if output_path:
        with Path(output_path).open("a", encoding="utf-8") as output:
            output.write("\n".join(lines) + "\n")
    else:
        print("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description="Gate archive publication to one release per month.")
    parser.add_argument("--status-report", default="conductor/archive_publication_status.json")
    parser.add_argument("--ledger", default="conductor/monthly_release_ledger.json")
    parser.add_argument("--release-version", default="")
    args = parser.parse_args()

    release_version = args.release_version.strip() or dt.datetime.now(dt.UTC).strftime("%Y-%m")
    already_published = already_published_this_release(
        Path(args.status_report),
        release_version,
    ) or release_version_in_ledger(
        Path(args.ledger),
        release_version,
    )
    write_github_output(
        {
            "release_version": release_version,
            "should_publish": str(not already_published).lower(),
            "already_published": str(already_published).lower(),
        }
    )


if __name__ == "__main__":
    main()
