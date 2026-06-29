import argparse
import json
from pathlib import Path
from typing import Any

from scripts.archive_manual_seed import _seed_posts

DEFAULT_ROOT = Path("manual_archive_seeds/threads")


def validate_seed(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        posts = _seed_posts(payload)
    except Exception as exc:  # noqa: BLE001 - validation report should preserve per-file failures.
        return {
            "path": str(path).replace("\\", "/"),
            "status": "invalid",
            "error": str(exc),
            "record_count": 0,
        }
    dates = [str(post.get("created_at") or "") for post in posts if post.get("created_at")]
    return {
        "path": str(path).replace("\\", "/"),
        "status": "valid",
        "record_count": len(posts),
        "min_created_at": min(dates) if dates else "",
        "max_created_at": max(dates) if dates else "",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate authorized Threads manual seed exports.")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--report", type=Path, default=Path("conductor/threads_manual_seed_validation_report.json"))
    parser.add_argument("--allow-empty", action="store_true")
    args = parser.parse_args()

    paths = sorted(
        path for path in args.root.glob("*.json")
        if path.is_file() and not path.name.endswith(".template.json") and path.name != "README.template.json"
    )
    results = [validate_seed(path) for path in paths]
    summary = {
        "seed_files": len(results),
        "valid": sum(1 for result in results if result["status"] == "valid"),
        "invalid": sum(1 for result in results if result["status"] == "invalid"),
        "records": sum(int(result.get("record_count") or 0) for result in results),
    }
    report = {"summary": summary, "results": results}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    if summary["invalid"]:
        raise SystemExit(1)
    if not args.allow_empty and summary["seed_files"] == 0:
        raise SystemExit("No Threads seed files found.")


if __name__ == "__main__":
    main()
