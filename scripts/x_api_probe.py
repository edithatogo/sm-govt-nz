import argparse
import json
import os
import time
from typing import Any

import tweepy


REQUIRED_ENV = ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"]


def run_probe(*, write_probe: bool = False) -> dict[str, Any]:
    missing = [name for name in REQUIRED_ENV if not os.getenv(name)]
    result: dict[str, Any] = {
        "valid": False,
        "missing": missing,
        "identity": None,
        "write_probe": None,
    }
    if missing:
        return result

    client = tweepy.Client(
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
    )
    try:
        me = client.get_me(user_auth=True)
        result["identity"] = {
            "ok": True,
            "id": str(me.data.id),
            "username": me.data.username,
            "name": me.data.name,
        }
    except Exception as error:  # pragma: no cover - exercised against live X
        result["identity"] = _error_result(error)
        return result

    if write_probe:
        marker = f"Courts mirror API write probe {int(time.time())} - deleting immediately"
        try:
            created = client.create_tweet(text=marker)
            tweet_id = str(created.data.get("id", ""))
            deleted = client.delete_tweet(tweet_id)
            result["write_probe"] = {
                "ok": True,
                "tweet_id": tweet_id,
                "deleted": bool(getattr(deleted, "data", {}).get("deleted", True)),
            }
        except Exception as error:  # pragma: no cover - exercised against live X
            result["write_probe"] = _error_result(error)
            return result

    result["valid"] = True
    return result


def _error_result(error: Exception) -> dict[str, str | bool]:
    return {
        "ok": False,
        "type": type(error).__name__,
        "message": str(error),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate live X API identity and optional write access.")
    parser.add_argument(
        "--write-probe",
        action="store_true",
        help="Create and immediately delete a probe post. Requires X API credits.",
    )
    args = parser.parse_args()

    result = run_probe(write_probe=args.write_probe)
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
