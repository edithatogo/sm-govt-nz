import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _load(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Record published monthly corpus releases in an append-only ledger.")
    parser.add_argument("--status-report", type=Path, default=Path("conductor/archive_publication_status.json"))
    parser.add_argument("--ledger", type=Path, default=Path("conductor/monthly_release_ledger.json"))
    args = parser.parse_args()

    status = _load(args.status_report, {})
    if status.get("mode") != "published":
        print("Status report is not a published release; ledger unchanged.")
        return
    release_version = str(status.get("release_version") or "")
    if not release_version:
        raise SystemExit("Published status report is missing release_version.")

    ledger = _load(args.ledger, {"generated_at": "", "releases": []})
    releases = [item for item in ledger.get("releases", []) if item.get("release_version") != release_version]
    releases.append(
        {
            "recorded_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "release_version": release_version,
            "mode": "published",
            "requested_targets": status.get("requested_targets", []),
            "artifact_sha256": (status.get("artifact") or {}).get("sha256", ""),
            "normalized_record_count": (status.get("artifact") or {}).get("normalized_record_count", 0),
            "hugging_face": (status.get("hugging_face") or {}).get("status", ""),
            "zenodo": (status.get("zenodo") or {}).get("status", ""),
        }
    )
    ledger = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "description": "Machine-maintained ledger of monthly cumulative corpus releases published externally.",
        "releases": sorted(releases, key=lambda item: item.get("release_version", "")),
    }
    args.ledger.parent.mkdir(parents=True, exist_ok=True)
    args.ledger.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Recorded published release {release_version}.")


if __name__ == "__main__":
    main()
