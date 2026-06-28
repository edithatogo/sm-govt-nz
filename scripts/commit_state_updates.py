import argparse
import os
import subprocess
from dataclasses import dataclass


@dataclass
class GitResult:
    returncode: int
    stdout: str
    stderr: str


def run_git(args: list[str], check: bool = True) -> GitResult:
    completed = subprocess.run(
        ["git", *args],
        check=False,
        capture_output=True,
        text=True,
    )
    result = GitResult(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
    if check and result.returncode != 0:
        details = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"git {' '.join(args)} failed: {details}")
    return result


def has_staged_changes() -> bool:
    return run_git(["diff", "--cached", "--quiet"], check=False).returncode != 0


def has_worktree_changes() -> bool:
    return bool(run_git(["status", "--porcelain"], check=False).stdout.strip())


def current_branch() -> str:
    ref_name = os.environ.get("GITHUB_REF_NAME")
    if ref_name:
        return ref_name
    return run_git(["rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()


def configure_identity() -> None:
    run_git(["config", "user.name", "github-actions[bot]"])
    run_git(["config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"])


def commit_selected_paths(message: str, paths: list[str], *, force: bool = False) -> bool:
    configure_identity()
    add_args = ["add"]
    if force:
        add_args.append("-f")
    run_git([*add_args, "--", *paths])
    if not has_staged_changes():
        print("No selected state updates to commit.")
        return False
    run_git(["commit", "-m", message])
    return True


def push_with_rebase(branch: str, max_attempts: int = 3) -> None:
    for attempt in range(1, max_attempts + 1):
        if has_worktree_changes():
            run_git(["stash", "push", "--include-untracked", "--message", "commit-state-updates-autostash"], check=False)
        run_git(["fetch", "origin", branch])
        run_git(["rebase", f"origin/{branch}"])
        pushed = run_git(["push", "origin", f"HEAD:{branch}"], check=False)
        if pushed.returncode == 0:
            print(f"Pushed state update to {branch}.")
            return
        if attempt == max_attempts:
            details = (pushed.stderr or pushed.stdout).strip()
            raise RuntimeError(f"Unable to push after {max_attempts} attempts: {details}")
        print(f"Push attempt {attempt} failed because the remote moved; retrying.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Commit and push workflow state updates.")
    parser.add_argument("--message", required=True)
    parser.add_argument("--path", action="append", required=True)
    parser.add_argument("--branch", default="")
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if not commit_selected_paths(args.message, args.path, force=args.force):
        return
    push_with_rebase(args.branch or current_branch(), max_attempts=args.max_attempts)


if __name__ == "__main__":
    main()
