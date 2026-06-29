import argparse
import json
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _published_target_count(status: dict[str, Any]) -> int:
    return sum(
        1
        for key in ("hugging_face", "zenodo", "osf")
        if isinstance(status.get(key), dict) and status[key].get("status") == "published"
    )


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return [f"{path} does not exist"]
    try:
        status = _load(path)
    except json.JSONDecodeError as exc:
        return [f"{path} is not valid JSON: {exc}"]
    mode = status.get("mode")
    release_version = str(status.get("release_version") or "")
    if not release_version:
        errors.append("release_version is required")
    if mode == "published":
        if _published_target_count(status) == 0:
            errors.append("published mode requires at least one published external target")
        requested = status.get("requested_targets")
        if not isinstance(requested, list) or not requested:
            errors.append("published mode requires non-empty requested_targets")
    elif mode == "artifact_only":
        if _published_target_count(status) > 0:
            errors.append("artifact_only mode must not include published external targets")
    else:
        errors.append(f"unsupported mode: {mode!r}")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate archive publication status invariants.")
    parser.add_argument("--status-report", type=Path, default=Path("conductor/archive_publication_status.json"))
    args = parser.parse_args()
    errors = validate(args.status_report)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print(f"Publication status OK: {args.status_report}")


if __name__ == "__main__":
    main()
