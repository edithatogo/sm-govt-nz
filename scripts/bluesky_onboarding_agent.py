"""Local operator-supervised Bluesky onboarding policy agent."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.bluesky_mirror_programme import load_registry
from src.bluesky_onboarding_heuristics import (
    DEFAULT_PILOT_REPORT,
    choose_plan,
    load_pilot_report,
    load_state,
    rank_candidates,
    record_event,
    save_state,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    plan_command = sub.add_parser("plan")
    plan_command.add_argument("--limit", type=int, default=10)
    plan_command.add_argument("--pilot-report", default=str(DEFAULT_PILOT_REPORT))
    record = sub.add_parser("record")
    record.add_argument("mirror_id")
    record.add_argument("outcome")
    record.add_argument("--plan", default=None)
    args = parser.parse_args()
    state = load_state()
    if args.command == "plan":
        selected = rank_candidates(
            load_registry(),
            state,
            load_pilot_report(args.pilot_report),
        )[: max(0, args.limit)]
        plan = choose_plan(state)
        print(
            json.dumps(
                {"plan": plan.name, "steps": plan.steps, "candidates": selected},
                indent=2,
            )
        )
        return
    plan = args.plan or choose_plan(state).name
    print(json.dumps(record_event(state, args.mirror_id, args.outcome, plan), indent=2))
    save_state(state)


if __name__ == "__main__":
    main()
