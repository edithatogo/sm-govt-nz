import json
import os
import sys

import datetime

# Add the project root to sys.path to import src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.bluesky import BlueskyApiClient

REGISTRY_PATH = "registry/agencies.json"
MIRROR_ACCOUNTS_PATH = "config/mirror_accounts.json"
FOLLOW_STATE_PATH = "conductor/follow_sync_state.json"


def load_registry():
    if not os.path.exists(REGISTRY_PATH):
        print(f"Error: Registry not found at {REGISTRY_PATH}")
        return []
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_mirror_accounts():
    if not os.path.exists(MIRROR_ACCOUNTS_PATH):
        return {"mirrors": []}
    with open(MIRROR_ACCOUNTS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_follow_state():
    if os.path.exists(FOLLOW_STATE_PATH):
        with open(FOLLOW_STATE_PATH, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {"last_updated": None, "follows": []}
    return {"last_updated": None, "follows": []}


def save_follow_state(results):
    state = {
        "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "follows": [],
    }

    for res in results:
        follow_entry = {
            "platform": res["platform"],
            "follower": res["follower"],
            "target": res["target"],
            "status": res["status"],
            "last_checked": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        if res.get("target_did"):
            follow_entry["target_did"] = res["target_did"]
        if res.get("evidence"):
            follow_entry["evidence"] = res["evidence"]
        if res.get("error"):
            follow_entry["error"] = res["error"]

        state["follows"].append(follow_entry)

    os.makedirs(os.path.dirname(FOLLOW_STATE_PATH), exist_ok=True)
    with open(FOLLOW_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    print(f"\nFollow state persisted to {FOLLOW_STATE_PATH}")


def generate_follow_matrix(registry, mirror_accounts=None):
    """
    Generates a matrix of required mirror follows per platform.
    Returns: { platform: [ (follower_handle, target_handle), ... ] }
    """
    mirror_accounts = mirror_accounts or {"mirrors": []}
    matrix = {}
    platform_handles = {}
    for agency in registry:
        profiles = agency.get("social_profiles", {})
        for platform, profile in profiles.items():
            if profile.get("status") == "active":
                if platform not in platform_handles:
                    platform_handles[platform] = []
                platform_handles[platform].append(profile["handle"])

    for mirror in mirror_accounts.get("mirrors", []):
        if mirror.get("status") != "active":
            continue
        platform = mirror["platform"]
        follower = mirror["handle"]
        target_policy = mirror.get("target_registry", "active_platform_accounts")
        if target_policy != "active_platform_accounts":
            continue
        targets = platform_handles.get(platform, [])
        matrix.setdefault(platform, [])
        for target in targets:
            if follower != target:
                matrix[platform].append((follower, target))

    for platform, follows in matrix.items():
        matrix[platform] = sorted(set(follows))
    return matrix


def check_bluesky_follows(matrix):
    """Check follows on Bluesky using public XRPC."""
    client = BlueskyApiClient()
    results = []
    did_cache = {}

    # Group by follower to minimize API calls
    follows_by_follower = {}
    for follower, target in matrix.get("bluesky", []):
        if follower not in follows_by_follower:
            follows_by_follower[follower] = []
        follows_by_follower[follower].append(target)

    for follower, targets in follows_by_follower.items():
        print(f"Checking follows for Bluesky actor: {follower}...")
        try:
            # getRelationships supports multiple 'others'
            relationships = client.get_relationships(follower, targets)

            # Map results
            rel_map = {rel.get("handle") or rel.get("did"): rel for rel in relationships}

            for target in targets:
                rel = rel_map.get(target, {})
                target_did = rel.get("did")
                if not target_did:
                    target_did = did_cache.setdefault(target, client.resolve_handle(target))
                # If following is present, it's the URI of the follow record
                is_following = bool(rel.get("following"))
                results.append(
                    {
                        "platform": "bluesky",
                        "follower": follower,
                        "target": target,
                        "target_did": target_did,
                        "status": "following" if is_following else "not_following",
                        "evidence": rel.get("following") if is_following else None,
                    }
                )
        except Exception as e:
            print(f"Error checking follows for {follower}: {e}")
            for target in targets:
                results.append(
                    {
                        "platform": "bluesky",
                        "follower": follower,
                        "target": target,
                        "status": "error",
                        "error": str(e),
                    }
                )
    return results


def main():
    # Ensure stdout handles UTF-8 (e.g. for Māori characters)
    if sys.stdout.encoding.lower() != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except AttributeError:
            # Fallback for older python versions if needed
            pass

    registry = load_registry()
    mirror_accounts = load_mirror_accounts()
    matrix = generate_follow_matrix(registry, mirror_accounts)

    all_results = []

    # Check supported platforms
    if "bluesky" in matrix:
        all_results.extend(check_bluesky_follows(matrix))

    # Identify unsupported platforms for manual review
    unsupported_platforms = [p for p in matrix.keys() if p != "bluesky"]
    for platform in unsupported_platforms:
        print(
            f"Platform {platform} is not currently supported for automated follow checks. Marking for manual review."
        )
        for follower, target in matrix[platform]:
            all_results.append(
                {
                    "platform": platform,
                    "follower": follower,
                    "target": target,
                    "status": "manual_review_required",
                }
            )

    # Output results
    print("\nFollow Sync Status Report:")
    print("-" * 60)
    for res in all_results:
        status_symbol = "V" if res["status"] == "following" else "X"
        if res["status"] == "manual_review_required":
            status_symbol = "?"
        elif res["status"] == "error":
            status_symbol = "!"

        print(
            f"[{status_symbol}] [{res['platform']}] {res['follower']} -> {res['target']} ({res['status']})"
        )

    # Update state cache (Phase 2)
    save_follow_state(all_results)


if __name__ == "__main__":
    main()
