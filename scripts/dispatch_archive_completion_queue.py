"""Dispatch bounded, deduplicated actions from the archive completion work queue."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


def load_queue(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def select_dispatches(queue: dict[str, Any], max_actions: int) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in queue.get("items", []):
        dispatch = item.get("dispatch") or {}
        if not dispatch.get("dispatchable"):
            continue
        inputs = dispatch.get("inputs") or {}
        concurrency_lane = {
            "workflow": dispatch.get("workflow"),
            "source_type": inputs.get("source_type"),
            "offset_sources": inputs.get("offset_sources", "0"),
        }
        signature = json.dumps(concurrency_lane, sort_keys=True)
        if signature in seen:
            continue
        seen.add(signature)
        selected.append(dispatch)
        if max_actions > 0 and len(selected) >= max_actions:
            break
    return selected


def command_for(dispatch: dict[str, Any], ref: str) -> list[str]:
    command = ["gh", "workflow", "run", str(dispatch["workflow"]), "--ref", ref]
    for key, value in sorted((dispatch.get("inputs") or {}).items()):
        command.extend(["--field", f"{key}={value}"])
    return command


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", type=Path, default=Path("conductor/archive_completion_work_queue.json"))
    parser.add_argument("--max-actions", type=int, default=5)
    parser.add_argument("--ref", default="master")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    dispatches = select_dispatches(load_queue(args.queue), args.max_actions)
    for dispatch in dispatches:
        command = command_for(dispatch, args.ref)
        print(" ".join(command))
        if args.execute:
            subprocess.run(command, check=True)
    print(f"Selected {len(dispatches)} bounded completion actions.")


if __name__ == "__main__":
    main()
