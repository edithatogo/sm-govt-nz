import argparse
import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any


def build_rotation_status(
    *,
    expires_on: str,
    today: str | None = None,
    warn_days: int = 30,
    critical_days: int = 7,
) -> dict[str, Any]:
    expiry_date = date.fromisoformat(expires_on)
    current_date = date.fromisoformat(today) if today else datetime.now(UTC).date()
    days_remaining = (expiry_date - current_date).days

    if days_remaining < 0:
        status = "expired"
    elif days_remaining <= critical_days:
        status = "critical"
    elif days_remaining <= warn_days:
        status = "warning"
    else:
        status = "ok"

    return {
        "status": status,
        "due": status != "ok",
        "expires_on": expiry_date.isoformat(),
        "checked_on": current_date.isoformat(),
        "days_remaining": days_remaining,
        "warn_days": warn_days,
        "critical_days": critical_days,
        "issue_title": "Buffer API key rotation due",
        "issue_body": _issue_body(
            status=status,
            expires_on=expiry_date,
            checked_on=current_date,
            days_remaining=days_remaining,
        ),
    }


def write_github_output(status: dict[str, Any], output_path: str | Path) -> None:
    lines = [
        f"status={status['status']}",
        f"due={str(status['due']).lower()}",
        f"expires_on={status['expires_on']}",
        f"checked_on={status['checked_on']}",
        f"days_remaining={status['days_remaining']}",
        f"issue_title={status['issue_title']}",
    ]
    Path(output_path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_issue_body(status: dict[str, Any], output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(status["issue_body"], encoding="utf-8")


def _issue_body(
    *,
    status: str,
    expires_on: date,
    checked_on: date,
    days_remaining: int,
) -> str:
    return (
        "# Buffer API Key Rotation\n\n"
        f"- Status: `{status}`\n"
        f"- Checked on: `{checked_on.isoformat()}`\n"
        f"- Current expiry: `{expires_on.isoformat()}`\n"
        f"- Days remaining: `{days_remaining}`\n\n"
        "Rotate the Buffer API key before expiry, update the repository secret "
        "`BUFFER_API_KEY`, and close this issue after the validation workflow "
        "passes with the new key.\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Check Buffer API key rotation window.")
    parser.add_argument("--expires-on", required=True, help="Current Buffer API key expiry date.")
    parser.add_argument("--today", help="Override today's date for tests.")
    parser.add_argument("--warn-days", type=int, default=30)
    parser.add_argument("--critical-days", type=int, default=7)
    parser.add_argument("--json-output")
    parser.add_argument("--issue-body-output")
    parser.add_argument("--github-output")
    parser.add_argument("--fail-on-expired", action="store_true")
    args = parser.parse_args()

    status = build_rotation_status(
        expires_on=args.expires_on,
        today=args.today,
        warn_days=args.warn_days,
        critical_days=args.critical_days,
    )
    if args.json_output:
        Path(args.json_output).write_text(
            json.dumps(status, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if args.issue_body_output:
        write_issue_body(status, args.issue_body_output)
    if args.github_output:
        write_github_output(status, args.github_output)

    if status["status"] == "ok":
        print(f"Buffer API key rotation is not due for {status['days_remaining']} days.")
    elif status["status"] == "expired":
        print(f"::error::Buffer API key expired {-status['days_remaining']} days ago.")
    else:
        print(
            "::warning::Buffer API key rotation is "
            f"{status['status']} with {status['days_remaining']} days remaining."
        )

    if args.fail_on_expired and status["status"] == "expired":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
