"""Generate a combined Meta platform (Instagram + Facebook) readiness status report.

Runs both Instagram and Facebook readiness checks and writes a combined JSON
report to conductor/meta_platform_status.json.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_facebook_readiness import check_readiness as check_fb_readiness
from scripts.check_instagram_readiness import check_readiness as check_ig_readiness


CONDUCTOR_DIR = Path("conductor")
REPORT_FILENAME = "meta_platform_status.json"
REPORT_PATH = CONDUCTOR_DIR / REPORT_FILENAME


def generate_report(
    env: dict[str, str] | None = None,
    *,
    skip_test_run: bool = False,
) -> dict[str, Any]:
    """Run Instagram and Facebook readiness checks and produce a combined report."""
    instagram = check_ig_readiness(env, skip_test_run=skip_test_run)
    facebook = check_fb_readiness(env, skip_test_run=skip_test_run)

    overall_ready = instagram["ready"] and facebook["ready"]
    all_blockers: list[str] = []
    all_blockers.extend(
        f"[instagram] {b}" for b in instagram.get("blockers", [])
    )
    all_blockers.extend(
        f"[facebook] {b}" for b in facebook.get("blockers", [])
    )

    report: dict[str, Any] = {
        "meta": {
            "title": "Meta Platform Readiness Status",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "overall_ready": overall_ready,
            "total_blockers": len(all_blockers),
        },
        "summary": {
            "instagram": {
                "ready": instagram["ready"],
                "blockers_count": len(instagram.get("blockers", [])),
                "secrets_ok": instagram["secrets"]["status"] == "passed",
                "config_ok": instagram["config"]["status"] == "passed",
                "tests_ok": instagram["adapter_tests"]["status"] == "passed"
                if instagram["adapter_tests"]["status"] != "skipped"
                else None,
            },
            "facebook": {
                "ready": facebook["ready"],
                "blockers_count": len(facebook.get("blockers", [])),
                "secrets_ok": facebook["secrets"]["status"] == "passed",
                "config_ok": facebook["config"]["status"] == "passed",
                "tests_ok": facebook["adapter_tests"]["status"] == "passed"
                if facebook["adapter_tests"]["status"] != "skipped"
                else None,
            },
        },
        "blockers": all_blockers,
        "instagram": instagram,
        "facebook": facebook,
    }

    return report


def write_report(report: dict[str, Any], path: str | Path = REPORT_PATH) -> Path:
    """Write the report to a JSON file."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def main() -> None:
    parser = __import__("argparse").ArgumentParser(
        description="Generate combined Meta platform readiness status report."
    )
    parser.add_argument(
        "--output",
        default=str(REPORT_PATH),
        help=f"Output path (default: {REPORT_PATH})",
    )
    parser.add_argument(
        "--skip-test-run",
        action="store_true",
        help="Skip running adapter tests (check existence only)",
    )
    parser.add_argument("--json", action="store_true", help="Print report to stdout")
    args = parser.parse_args()

    report = generate_report(skip_test_run=args.skip_test_run)
    output_path = write_report(report, args.output)

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))

    print(f"Meta platform status report written to {output_path}")
    if report["meta"]["overall_ready"]:
        print("Both Instagram and Facebook are ready for launch.")
    else:
        print(f"Blockers remaining: {report['meta']['total_blockers']}")
        for blocker in report["blockers"]:
            print(f"  - {blocker}")

    sys.exit(0 if report["meta"]["overall_ready"] else 1)


if __name__ == "__main__":
    main()
