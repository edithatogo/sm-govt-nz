"""Local operator-supervised Bluesky onboarding policy agent."""

from __future__ import annotations

import argparse
import json

from src.bluesky_mirror_programme import load_registry
from src.bluesky_onboarding_heuristics import choose_plan, load_state, rank_candidates, record_event, save_state


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("plan")
    record = sub.add_parser("record")
    record.add_argument("mirror_id")
    record.add_argument("outcome")
    record.add_argument("--plan", default=None)
    args = parser.parse_args()
    state = load_state()
    if args.command == "plan":
        selected = rank_candidates(load_registry(), state)
        plan = choose_plan(state)
        print(json.dumps({"plan": plan.name, "steps": plan.steps, "candidates": selected}, indent=2))
        return
    plan = args.plan or choose_plan(state).name
    print(json.dumps(record_event(state, args.mirror_id, args.outcome, plan), indent=2))
    save_state(state)


if __name__ == "__main__":
    main()
