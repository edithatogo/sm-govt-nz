import argparse
import subprocess
from pathlib import Path


def changed_paths(paths: list[str], *, cwd: str | Path = ".") -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", "--", *paths],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def assert_noop(paths: list[str], *, cwd: str | Path = ".") -> None:
    changed = changed_paths(paths, cwd=cwd)
    if changed:
        formatted = "\n".join(f"- {path}" for path in changed)
        raise RuntimeError(f"No-op check failed; these paths changed:\n{formatted}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fail when a no-op command changed tracked files.")
    parser.add_argument("paths", nargs="+")
    args = parser.parse_args()

    assert_noop(args.paths)
    print("No-op check passed. No tracked files changed.")


if __name__ == "__main__":
    main()
