import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
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


def validate_mirrors(
    *,
    mirror_url: str | None = None,
    branch: str = "master",
    compare_head: bool = False,
    runner=subprocess.run,
) -> MirrorValidation:
    active_mirror_url = mirror_url if mirror_url is not None else os.getenv("GIT_MIRROR_URL", "")
    if not active_mirror_url:
        return MirrorValidation(
            status="missing_mirror_url",
            mirror_url_present=False,
            ssh_access_checked=False,
            remote_alignment_checked=False,
            detail="GIT_MIRROR_URL environment variable is not set.",
        )

    host = mirror_host(active_mirror_url)
    ssh_checked = False
    if active_mirror_url.startswith("git@"):
        ssh_checked = True
        if not check_ssh_access(host, runner=runner):
            return MirrorValidation(
                status="ssh_access_failed",
                mirror_url_present=True,
                ssh_access_checked=True,
                remote_alignment_checked=False,
                detail=f"Failed to validate SSH access to {host}.",
            )

    if not compare_head:
        return MirrorValidation(
            status="ok",
            mirror_url_present=True,
            ssh_access_checked=ssh_checked,
            remote_alignment_checked=False,
            detail="Mirror URL is configured.",
        )

    local_head = git_output(["git", "rev-parse", branch], runner=runner)
    remote_head = remote_branch_head(active_mirror_url, branch, runner=runner)
    if not remote_head:
        return MirrorValidation(
            status="remote_branch_missing",
            mirror_url_present=True,
            ssh_access_checked=ssh_checked,
            remote_alignment_checked=True,
            local_head=local_head,
            remote_head="",
            detail=f"Remote branch {branch} was not found.",
        )
    if local_head != remote_head:
        return MirrorValidation(
            status="remote_misaligned",
            mirror_url_present=True,
            ssh_access_checked=ssh_checked,
            remote_alignment_checked=True,
            local_head=local_head,
            remote_head=remote_head,
            detail=f"Remote {branch} is not aligned with local {branch}.",
        )
    return MirrorValidation(
        status="ok",
        mirror_url_present=True,
        ssh_access_checked=ssh_checked,
        remote_alignment_checked=True,
        local_head=local_head,
        remote_head=remote_head,
        detail=f"Remote {branch} is aligned.",
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate secondary Git mirror configuration.")
    parser.add_argument("--branch", default="master")
    parser.add_argument("--compare-head", action="store_true")
    args = parser.parse_args()

    result = validate_mirrors(branch=args.branch, compare_head=args.compare_head)
    print(result.detail)
    if result.remote_alignment_checked:
        print(f"local_head={result.local_head}")
        print(f"remote_head={result.remote_head}")
    if not result.ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
