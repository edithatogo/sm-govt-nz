import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Protocol

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.bluesky import BlueskyApiClient


class PostLookupClient(Protocol):
    def fetch_posts(self, uris: list[str]) -> list[Mapping[str, Any]]:
        """Return public post records for AT Protocol post URIs."""


def verify_archive_mirror_posts(
    *,
    state_path: str | Path = "conductor/archive_mirror_state.json",
    target: str = "bluesky",
    limit: int = 5,
    client: PostLookupClient | None = None,
) -> dict[str, Any]:
    deliveries = _load_deliveries(Path(state_path), target=target)
    sampled = deliveries[-limit:] if limit > 0 else deliveries
    uris = [delivery["detail"] for delivery in sampled if delivery["detail"].startswith("at://")]
    posts_by_uri = {
        str(post.get("uri") or ""): post
        for post in (client or BlueskyApiClient()).fetch_posts(uris)
    }

    results: list[dict[str, Any]] = []
    for delivery in sampled:
        uri = delivery["detail"]
        post = posts_by_uri.get(uri)
        results.append(
            {
                "record_id": delivery["record_id"],
                "uri": uri,
                "mirror_url": delivery["mirror_url"],
                "valid": post is not None,
            }
        )

    failures = [result for result in results if not result["valid"]]
    return {
        "checked": len(results),
        "failures": failures,
        "target": target,
        "valid": not failures,
    }


def _load_deliveries(state_path: Path, *, target: str) -> list[dict[str, str]]:
    if not state_path.exists():
        return []
    data = json.loads(state_path.read_text(encoding="utf-8"))
    posted_records = data.get("posted_records", {})
    if not isinstance(posted_records, dict):
        return []
    target_records = posted_records.get(target, {})
    if not isinstance(target_records, dict):
        return []

    deliveries: list[dict[str, str]] = []
    for source_deliveries in target_records.values():
        if not isinstance(source_deliveries, list):
            continue
        for delivery in source_deliveries:
            if not isinstance(delivery, dict):
                continue
            detail = str(delivery.get("detail") or "")
            if not detail.startswith("at://"):
                continue
            deliveries.append(
                {
                    "detail": detail,
                    "mirror_url": str(delivery.get("mirror_url") or ""),
                    "record_id": str(delivery.get("record_id") or ""),
                }
            )
    return deliveries


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify sampled archive mirror posts exist.")
    parser.add_argument("--state-path", default="conductor/archive_mirror_state.json")
    parser.add_argument("--target", default="bluesky")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = verify_archive_mirror_posts(
        state_path=args.state_path,
        target=args.target,
        limit=args.limit,
    )
    if args.json or not result["valid"]:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"Verified {result['checked']} archive mirror posts for {result['target']}.")
    raise SystemExit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
