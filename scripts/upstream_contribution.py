import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


def load_tool_config(path: str | Path = "config/upstream_tools.json") -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_issue_command(upstream: str, title: str, body: str) -> list[str]:
    return ["gh", "issue", "create", "--repo", upstream, "--title", title, "--body", body]


def build_fork_command(upstream: str, clone_dir: str) -> list[str]:
    return ["gh", "repo", "fork", upstream, "--clone", "--remote", "--fork-name", Path(clone_dir).name]


def build_pr_command(upstream: str, head: str, title: str, body: str) -> list[str]:
    return ["gh", "pr", "create", "--repo", upstream, "--head", head, "--title", title, "--body", body]


def run_command(command: list[str], *, dry_run: bool) -> dict[str, Any]:
    if dry_run:
        return {"command": command, "returncode": 0, "stdout": "", "stderr": "", "dry_run": True}
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "dry_run": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare upstream issue/fork/PR workflow commands.")
    parser.add_argument("tool", choices=sorted(load_tool_config().keys()))
    parser.add_argument("--title", required=True)
    parser.add_argument("--body", required=True)
    parser.add_argument("--clone-dir")
    parser.add_argument("--head")
    parser.add_argument("--create-issue", action="store_true")
    parser.add_argument("--fork", action="store_true")
    parser.add_argument("--create-pr", action="store_true")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    config = load_tool_config()[args.tool]
    upstream = config["upstream"]
    dry_run = not args.execute
    results = []

    if args.create_issue:
        results.append(run_command(build_issue_command(upstream, args.title, args.body), dry_run=dry_run))
    if args.fork:
        clone_dir = args.clone_dir or f"vendor-forks/{args.tool}"
        results.append(run_command(build_fork_command(upstream, clone_dir), dry_run=dry_run))
    if args.create_pr:
        if not args.head:
            raise ValueError("--head is required when --create-pr is used.")
        results.append(run_command(build_pr_command(upstream, args.head, args.title, args.body), dry_run=dry_run))

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
