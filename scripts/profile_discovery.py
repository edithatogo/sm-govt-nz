import argparse
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DiscoveryCandidate:
    agency_id: str
    name: str
    command: list[str]


def build_social_analyzer_command(
    name: str,
    *,
    command: str = "social-analyzer",
    platform: str | None = None,
) -> list[str]:
    args = [command, "--username", name, "--metadata"]
    if platform:
        args.extend(["--websites", platform])
    return args


def build_candidates(registry_path: str | Path, command: str = "social-analyzer") -> list[DiscoveryCandidate]:
    agencies = json.loads(Path(registry_path).read_text(encoding="utf-8"))
    candidates = []
    for agency in agencies:
        handle_seed = agency["name"].split("(")[0].strip()
        candidates.append(
            DiscoveryCandidate(
                agency_id=agency["agency_id"],
                name=agency["name"],
                command=build_social_analyzer_command(handle_seed, command=command),
            )
        )
    return candidates


def run_candidate(candidate: DiscoveryCandidate) -> dict[str, object]:
    completed = subprocess.run(candidate.command, capture_output=True, text=True, check=False)
    return {
        "agency_id": candidate.agency_id,
        "name": candidate.name,
        "command": candidate.command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare or run social profile discovery probes.")
    parser.add_argument("--registry", default="registry/agencies.json")
    parser.add_argument("--command", default="social-analyzer")
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()

    candidates = build_candidates(args.registry, command=args.command)
    payload = [run_candidate(candidate) if args.run else candidate.__dict__ for candidate in candidates]
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
