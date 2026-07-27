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
    credential_health_report,
    health_report,
    load_runtime_state,
    load_registry,
    pause,
    pilot_candidate_report,
    preflight_account,
    publish_next,
    recover_account,
    validate_registry,
    workflow_matrix,
    write_programme_report,
    write_registry,
)


def write_json_report(path: str | Path, result: dict[str, object]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def github_matrix_outputs(result: dict[str, object]) -> dict[str, object]:
    has_targets = bool(result.get("include"))
    safe_matrix = result
    if not has_targets:
        safe_matrix = {
            "include": [
                {
                    "skip": True,
                    "mirror_id": "__no_eligible_mirror__",
                    "environment": "__no_environment__",
                }
            ]
        }
    return {
        "matrix": safe_matrix,
        "selected_matrix": result,
        "has_targets": has_targets,
    }


def public_health_faults(result: dict[str, object]) -> list[str]:
    accounts = result.get("accounts", [])
    if not isinstance(accounts, list):
        raise ValueError("health report accounts must be a list")
    return sorted(
        str(account["mirror_id"])
        for account in accounts
        if isinstance(account, dict) and account.get("status") == "fault"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Operate the Bluesky agency mirror programme.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate")
    preflight = sub.add_parser("preflight")
    preflight.add_argument("--mirror-id", required=True)
    credential_health = sub.add_parser("credential-health")
    credential_health.add_argument("--mirror-id", required=True)
    credential_health.add_argument("--output", required=True)
    build = sub.add_parser("build-registry")
    build.add_argument("--manifest", default="conductor/govt_archive_source_manifest.json")
    matrix = sub.add_parser("matrix")
    matrix.add_argument(
        "--mode", choices=("preflight", "ongoing", "backfill", "health"), required=True
    )
    matrix.add_argument("--mirror-id", default="")
    matrix.add_argument("--github-output", action="store_true")
    publish = sub.add_parser("publish")
    publish.add_argument("--mode", choices=("ongoing", "backfill"), required=True)
    publish.add_argument("--mirror-id", required=True)
    publish.add_argument("--dry-run", action="store_true")
    health = sub.add_parser("health")
    health.add_argument("--output", default="conductor/bluesky_mirror_health_report.json")
    health.add_argument("--fail-on-fault", action="store_true")
    pilots = sub.add_parser("pilot-candidates")
    pilots.add_argument("--limit", type=int, default=10)
    pilots.add_argument("--archive-root", default="historical_archive_normalized")
    pilots.add_argument("--output", default="conductor/bluesky_mirror_pilot_candidates.json")
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
    elif args.command == "credential-health":
        result = credential_health_report(
            load_registry(),
            args.mirror_id,
            handle=os.environ.get("BLUESKY_HANDLE", ""),
            app_password=os.environ.get("BLUESKY_APP_PASSWORD", ""),
        )
        write_json_report(args.output, result)
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
            outputs = github_matrix_outputs(result)
            with Path(output).open("a", encoding="utf-8") as stream:
                stream.write(f"matrix={json.dumps(outputs['matrix'], separators=(',', ':'))}\n")
                stream.write(
                    "selected_matrix="
                    f"{json.dumps(outputs['selected_matrix'], separators=(',', ':'))}\n"
                )
                stream.write(f"has_targets={str(outputs['has_targets']).lower()}\n")
    elif args.command == "publish":
        result = publish_next(
            load_registry(),
            args.mirror_id,
            mode=args.mode,
            dry_run=args.dry_run,
            eligibility_report_path=(ELIGIBILITY_REPORT_DIR / f"{args.mirror_id}.json"),
        )
    elif args.command == "health":
        result = health_report(load_registry(), runtime_state=load_runtime_state())
        write_json_report(args.output, result)
        faults = public_health_faults(result)
        if args.fail_on_fault and faults:
            raise RuntimeError("Public Bluesky health failed for: " + ", ".join(sorted(faults)))
    elif args.command == "pilot-candidates":
        result = pilot_candidate_report(
            load_registry(),
            args.archive_root,
            limit=args.limit,
        )
        write_json_report(args.output, result)
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
