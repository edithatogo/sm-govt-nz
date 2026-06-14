import argparse
import datetime
import json
import os
import sys
from urllib.request import Request, urlopen

# Add the project root to sys.path to import src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FOLLOW_STATE_PATH = "conductor/follow_sync_state.json"


def load_follow_state():
    if not os.path.exists(FOLLOW_STATE_PATH):
        print(
            f"Error: Follow state not found at {FOLLOW_STATE_PATH}. Run scripts/check_follow_status.py first."
        )
        return None
    with open(FOLLOW_STATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def bluesky_login(handle, app_password, service_url="https://bsky.social"):
    payload = json.dumps({"identifier": handle, "password": app_password}).encode("utf-8")
    request = Request(
        f"{service_url.rstrip('/')}/xrpc/com.atproto.server.createSession",
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def bluesky_follow(access_token, follower_did, target_did, service_url="https://bsky.social"):
    now = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    payload = json.dumps(
        {
            "repo": follower_did,
            "collection": "app.bsky.graph.follow",
            "record": {"subject": target_did, "createdAt": now},
        }
    ).encode("utf-8")

    request = Request(
        f"{service_url.rstrip('/')}/xrpc/com.atproto.repo.createRecord",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        },
        method="POST",
    )
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def main():
    parser = argparse.ArgumentParser(description="Synchronize mirror follows using supported APIs.")
    parser.add_argument(
        "--dry-run", action="store_true", help="Report missing follows without executing."
    )
    parser.add_argument(
        "--execute", action="store_true", help="Execute missing follows for supported platforms."
    )

    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        parser.print_help()
        sys.exit(1)

    state = load_follow_state()
    if not state:
        sys.exit(1)

    mirror_handle = os.getenv("BLUESKY_MIRROR_HANDLE")
    app_password = os.getenv("BLUESKY_MIRROR_APP_PASSWORD")

    if args.execute and (not mirror_handle or not app_password):
        print(
            "Error: BLUESKY_MIRROR_HANDLE and BLUESKY_MIRROR_APP_PASSWORD required for --execute."
        )
        sys.exit(1)

    missing_follows = [
        f for f in state["follows"] if f["platform"] == "bluesky" and f["status"] == "not_following"
    ]

    if not missing_follows:
        print("No missing follows detected.")
        return

    print(f"Detected {len(missing_follows)} missing follows on Bluesky.")

    # We can only follow FROM the account we have credentials for
    work_list = [f for f in missing_follows if f["follower"] == mirror_handle]

    if not work_list:
        print(f"None of the missing follows are from the current mirror account ({mirror_handle}).")
        if mirror_handle:
            print(
                "Note: To sync all follows, you may need to run this script with credentials for each mirror account."
            )
        return

    print(f"Missing follows from current account ({mirror_handle}): {len(work_list)}")
    for f in work_list:
        print(f"  -> {f['target']} ({f.get('target_did', 'unknown DID')})")

    if args.dry_run:
        print("\nDry-run complete. No actions taken.")
        return

    if args.execute:
        print(f"\nLogging in as {mirror_handle}...")
        try:
            session = bluesky_login(mirror_handle, app_password)
            access_token = session["accessJwt"]
            follower_did = session["did"]

            for f in work_list:
                target_did = f.get("target_did")
                if not target_did:
                    print(f"Skipping {f['target']}: Missing target DID.")
                    continue

                print(f"Following {f['target']} ({target_did})...")
                try:
                    res = bluesky_follow(access_token, follower_did, target_did)
                    print(f"  Successfully followed. URI: {res.get('uri')}")
                except Exception as e:
                    print(f"  Error following {f['target']}: {e}")

            print(
                "\nFollow execution complete. Run scripts/check_follow_status.py to verify and update state."
            )
        except Exception as e:
            print(f"Login failed: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
