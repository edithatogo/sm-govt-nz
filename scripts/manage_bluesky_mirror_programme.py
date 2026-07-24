import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.bluesky_mirror_programme import (
    ELIGIBILITY_REPORT_DIR,
    STATE_PATH,
    build_registry_from_manifest,
    health_report,
    load_runtime_state,
    load_registry,
    pause,
    preflight_account,
    publish_next,
    recover_account,
    validate_registry,
    workflow_matrix,
    write_programme_report,
    write_registry,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Operate the Bluesky agency mirror programme.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate")
    preflight = sub.add_parser("preflight")
    preflight.add_argument("--mirror-id", required=True)
    build = sub.add_parser("build-registry")
    build.add_argument("--manifest", default="conductor/govt_archive_source_manifest.json")
    matrix = sub.add_parser("matrix")
    matrix.add_argument("--mode", choices=("preflight", "ongoing", "backfill", "health"), required=True)
    matrix.add_argument("--mirror-id", default="")
    matrix.add_argument("--github-output", action="store_true")
    publish = sub.add_parser("publish")
    publish.add_argument("--mode", choices=("ongoing", "backfill"), required=True)
    publish.add_argument("--mirror-id", required=True)
    publish.add_argument("--dry-run", action="store_true")
    health = sub.add_parser("health")
    health.add_argument("--output", default="conductor/bluesky_mirror_health_report.json")
    stop = sub.add_parser("pause")
    stop.add_argument("--mirror-id", required=True)
    stop.add_argument("--reason", required=True)
    recover = sub.add_parser("recover")
    recover.add_argument("--mirror-id", required=True)
    recover.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if args.command == "build-registry":
        existing = load_registry()
        manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
        registry = build_registry_from_manifest(manifest, existing)
        write_registry(registry)
        result = write_programme_report(registry)
    elif args.command == "validate":
        registry = load_registry()
        validate_registry(registry)
        result = write_programme_report(registry)
    elif args.command == "preflight":
        result = preflight_account(
            load_registry(),
            args.mirror_id,
            handle=os.environ.get("BLUESKY_HANDLE", ""),
            app_password=os.environ.get("BLUESKY_APP_PASSWORD", ""),
        )
    elif args.command == "matrix":
        state = load_runtime_state()
        result = workflow_matrix(
            load_registry(),
            mode=args.mode,
            mirror_id=args.mirror_id,
            runtime_state=state,
        )
        if args.github_output:
            output = os.environ.get("GITHUB_OUTPUT")
            if not output:
                raise RuntimeError("GITHUB_OUTPUT is required with --github-output.")
            with Path(output).open("a", encoding="utf-8") as stream:
                stream.write(f"matrix={json.dumps(result, separators=(',', ':'))}\n")
    elif args.command == "publish":
        result = publish_next(
            load_registry(),
            args.mirror_id,
            mode=args.mode,
            dry_run=args.dry_run,
            eligibility_report_path=(
                ELIGIBILITY_REPORT_DIR / f"{args.mirror_id}.json"
            ),
        )
    elif args.command == "health":
        result = health_report(load_registry(), runtime_state=load_runtime_state())
        Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    elif args.command == "pause":
        result = pause(STATE_PATH, args.mirror_id, args.reason)
    else:
        result = recover_account(
            load_registry(),
            args.mirror_id,
            apply=args.apply,
        )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
