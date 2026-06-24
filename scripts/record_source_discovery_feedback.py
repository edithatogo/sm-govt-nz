import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_CONFIG = Path("config/govt_source_discovery.json")

def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def load_json(path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)

def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def main():
    parser = argparse.ArgumentParser(description="Record source-discovery feedback for heuristic improvement.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--agency-id", required=True)
    parser.add_argument("--platform", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--decision", required=True, choices=["accepted", "rejected", "needs_review"])
    parser.add_argument("--reason", default="")
    parser.add_argument("--heuristic", action="append", default=[])
    args = parser.parse_args()
    config = load_json(args.config)
    learning_path = Path(config.get("heuristics", {}).get("learning_file", "conductor/govt_source_discovery_learning.json"))
    if learning_path.exists():
        learning = load_json(learning_path)
    else:
        learning = {"generated_at": now_iso(), "entries": []}
    learning["entries"].append({"recorded_at": now_iso(), "candidate_id": args.candidate_id, "agency_id": args.agency_id, "platform": args.platform, "url": args.url, "decision": args.decision, "reason": args.reason, "heuristics": args.heuristic})
    learning["generated_at"] = now_iso()
    write_json(learning_path, learning)
    print(f"recorded {args.decision} feedback for {args.candidate_id}")

if __name__ == "__main__":
    main()
