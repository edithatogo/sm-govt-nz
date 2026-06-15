"""
Validate secondary Git mirror configuration.

Outputs a structured JSON report to stdout (and optionally to a file)
and exits non-zero on failure so it can be used in CI pipelines.

Supports:
  --dry-run              perform checks but skip any real remote access
  --compare-head         fetch and compare local vs remote HEAD
  --output FILE          write JSON report to a file as well as stdout
  --branch BRANCH        which branch to compare (default: master)
"""

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence


@dataclass(frozen=True)
class MirrorValidation:
    status: str
    mirror_url_present: bool
    ssh_access_checked: bool
    remote_alignment_checked: bool
    local_head: str = ""
    remote_head: str = ""
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.status == "ok"

    def to_json(self) -> dict:
        """Serialise to a JSON-compatible dict."""
        return {
            "status": self.status,
            "ok": self.ok,
            "mirror_url_present": self.mirror_url_present,
            "ssh_access_checked": self.ssh_access_checked,
            "remote_alignment_checked": self.remote_alignment_checked,
            "local_head": self.local_head,
            "remote_head": self.remote_head,
            "detail": self.detail,
        }


def validate_mirrors(
    *,
    mirror_url: str | None = None,
    branch: str = "master",
    compare_head: bool = False,
    dry_run: bool = False,
    runner=subprocess.run,
) -> MirrorValidation:
    active_mirror_url = mirror_url if mirror_url is not None else os.getenv("GIT_MIRROR_URL", "")
    if not active_mirror_url:
        return MirrorValidation(
            status="missing_mirror_url",
            mirror_url_present=False,
            ssh_access_checked=False,
            remote_alignment_checked=False,
            detail="GIT_MIRROR_URL environment variable is not set. No mirror remote configured.",
        )

    host = mirror_host(active_mirror_url)
    ssh_checked = False
    if active_mirror_url.startswith("git@"):
        ssh_checked = True
        if dry_run:
            # Skip actual SSH in dry-run mode
            pass
        elif not check_ssh_access(host, runner=runner):
            return MirrorValidation(
                status="ssh_access_failed",
                mirror_url_present=True,
                ssh_access_checked=True,
                remote_alignment_checked=False,
                detail=f"Failed to validate SSH access to {host}. "
                "Check that the SSH private key is configured and the host key is trusted.",
            )

    if not compare_head:
        return MirrorValidation(
            status="ok",
            mirror_url_present=True,
            ssh_access_checked=ssh_checked,
            remote_alignment_checked=False,
            detail="Mirror URL is configured and SSH access checked (if applicable).",
        )

    # --- compare HEAD -------------------------------------------------------
    try:
        local_head = git_output(["git", "rev-parse", branch], runner=runner)
    except RuntimeError as exc:
        return MirrorValidation(
            status="local_branch_missing",
            mirror_url_present=True,
            ssh_access_checked=ssh_checked,
            remote_alignment_checked=False,
            detail=f"Could not resolve local branch '{branch}': {exc}",
        )

    if dry_run:
        # In dry-run mode we still report local HEAD but skip remote fetch.
        return MirrorValidation(
            status="ok",
            mirror_url_present=True,
            ssh_access_checked=ssh_checked,
            remote_alignment_checked=False,
            local_head=local_head,
            detail=f"[dry-run] Would compare local '{branch}' ({local_head}) with remote.",
        )

    try:
        remote_head = remote_branch_head(active_mirror_url, branch, runner=runner)
    except RuntimeError as exc:
        return MirrorValidation(
            status="remote_lookup_failed",
            mirror_url_present=True,
            ssh_access_checked=ssh_checked,
            remote_alignment_checked=False,
            local_head=local_head,
            detail=f"Failed to query remote branch '{branch}': {exc}",
        )

    if not remote_head:
        return MirrorValidation(
            status="remote_branch_missing",
            mirror_url_present=True,
            ssh_access_checked=ssh_checked,
            remote_alignment_checked=True,
            local_head=local_head,
            remote_head="",
            detail=f"Remote branch '{branch}' was not found at the configured mirror URL.",
        )
    if local_head != remote_head:
        return MirrorValidation(
            status="remote_misaligned",
            mirror_url_present=True,
            ssh_access_checked=ssh_checked,
            remote_alignment_checked=True,
            local_head=local_head,
            remote_head=remote_head,
            detail=f"Remote '{branch}' ({remote_head}) is NOT aligned with local '{branch}' ({local_head}).",
        )
    return MirrorValidation(
        status="ok",
        mirror_url_present=True,
        ssh_access_checked=ssh_checked,
        remote_alignment_checked=True,
        local_head=local_head,
        remote_head=remote_head,
        detail=f"Remote '{branch}' ({remote_head}) is aligned with local '{branch}'.",
    )


def mirror_host(mirror_url: str) -> str:
    if mirror_url.startswith("git@"):
        return mirror_url.split("@", 1)[1].split(":", 1)[0]
    if "://" in mirror_url:
        return mirror_url.split("://", 1)[1].split("/", 1)[0]
    return ""


def check_ssh_access(host: str, *, runner=subprocess.run) -> bool:
    if not host:
        return False
    result = runner(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", f"git@{host}"],
        capture_output=True,
        text=True,
        check=False,
    )
    output = f"{getattr(result, 'stdout', '')}\n{getattr(result, 'stderr', '')}"
    return "successfully authenticated" in output


def remote_branch_head(
    mirror_url: str,
    branch: str,
    *,
    runner=subprocess.run,
) -> str:
    output = git_output(["git", "ls-remote", mirror_url, f"refs/heads/{branch}"], runner=runner)
    if not output:
        return ""
    return output.split()[0]


def git_output(command: Sequence[str], *, runner=subprocess.run) -> str:
    completed = runner(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        stderr = getattr(completed, "stderr", "").strip()
        raise RuntimeError(stderr or f"Command failed: {' '.join(command)}")
    return getattr(completed, "stdout", "").strip()


def build_report(validation: MirrorValidation) -> dict:
    """Wrap the validation result in a top-level report envelope."""
    return {
        "tool": "validate_git_mirrors",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "validation": validation.to_json(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate secondary Git mirror configuration and output a structured JSON report."
    )
    parser.add_argument("--branch", default="master", help="Branch to compare (default: master)")
    parser.add_argument(
        "--compare-head",
        action="store_true",
        help="Also compare local HEAD with the remote mirror HEAD",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform checks but skip actual remote SSH/git operations",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional file path to write the JSON report to",
    )
    args = parser.parse_args()

    result = validate_mirrors(
        branch=args.branch,
        compare_head=args.compare_head,
        dry_run=args.dry_run,
    )

    report = build_report(result)
    report_json = json.dumps(report, indent=2)

    # Always print to stdout so CI logs capture the report.
    print(report_json)

    # Optionally write to a file for downstream consumption.
    if args.output:
        output_path = os.path.abspath(args.output)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_json)
        print(f"Report written to {output_path}", file=sys.stderr)

    if not result.ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
