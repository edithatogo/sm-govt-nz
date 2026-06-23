from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def check_version_consistency() -> list[str]:
    failures: list[str] = []

    pyproject = tomllib.loads(_text("pyproject.toml"))
    package_version = str(pyproject["project"]["version"])
    if not SEMVER_RE.fullmatch(package_version):
        failures.append(f"Version is not SemVer-like: {package_version}")

    return failures


def main() -> int:
    failures = check_version_consistency()
    if failures:
        for f in failures:
            print(f"ERROR: {f}")
        return 1
    print("Version consistency checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
