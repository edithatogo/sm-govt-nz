import argparse
import json
import os
from pathlib import Path
from typing import Any


def load_schema(path: str | Path = "config/secrets.schema.json") -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_environment(
    mode: str,
    *,
    schema: dict[str, Any] | None = None,
    env: dict[str, str] | None = None,
    target: str | None = None,
) -> dict[str, Any]:
    active_schema = schema or load_schema()
    active_env = env if env is not None else dict(os.environ)
    modes = active_schema["modes"]
    if mode not in modes:
        raise ValueError(f"Unknown secret validation mode: {mode}")

    mode_schema = modes[mode]
    missing_required = [
        name for name in mode_schema.get("required", []) if not active_env.get(name)
    ]
    any_of = mode_schema.get("anyOf", [])
    satisfied_groups = [
        group["name"]
        for group in any_of
        if all(active_env.get(name) for name in group.get("vars", []))
    ]
    json_errors = _validate_json_vars(active_schema.get("jsonVars", []), active_env)
    target_errors = _validate_target(target, active_env) if target else []
    valid = (
        not missing_required
        and not json_errors
        and not target_errors
        and (not any_of or bool(satisfied_groups))
    )

    return {
        "mode": mode,
        "target": target,
        "valid": valid,
        "missing_required": missing_required,
        "satisfied_groups": satisfied_groups,
        "requires_one_of": [group["name"] for group in any_of],
        "json_errors": json_errors,
        "target_errors": target_errors,
    }


def load_env_file(path: str | Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path:
        return env
    env_path = Path(path)
    if not env_path.exists() or env_path.is_dir():
        return env

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, value = stripped.split("=", 1)
        name = name.strip()
        value = value.strip().strip('"').strip("'")
        if name:
            env[name] = value
    return env


def _validate_json_vars(names: list[str], env: dict[str, str]) -> list[str]:
    errors = []
    for name in names:
        value = env.get(name)
        if not value:
            continue
        try:
            json.loads(value)
        except json.JSONDecodeError as error:
            errors.append(f"{name}: {error.msg}")
    return errors


def _validate_target(target: str | None, env: dict[str, str]) -> list[str]:
    if target == "bluesky":
        has_bluesky = bool(env.get("BLUESKY_MIRROR_HANDLE")) and bool(
            env.get("BLUESKY_MIRROR_APP_PASSWORD")
        )
        if has_bluesky:
            return []
        return [
            "bluesky: require BLUESKY_MIRROR_HANDLE and BLUESKY_MIRROR_APP_PASSWORD"
        ]

    if target == "threads":
        has_threads = bool(env.get("THREADS_ACCESS_TOKEN")) and (
            bool(env.get("THREADS_USER_ID")) or bool(env.get("THREADS_MIRROR_ACCOUNT_ID"))
        )
        if has_threads:
            return []
        return [
            "threads: require THREADS_ACCESS_TOKEN and THREADS_USER_ID "
            "(THREADS_MIRROR_ACCOUNT_ID is accepted as a legacy alias)"
        ]

    if target == "instagram":
        has_instagram = bool(env.get("INSTAGRAM_ACCESS_TOKEN")) and bool(
            env.get("INSTAGRAM_USER_ID")
        )
        if has_instagram:
            return []
        return [
            "instagram: require INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_USER_ID"
        ]

    if target == "facebook":
        has_facebook_page = bool(env.get("FACEBOOK_PAGE_ACCESS_TOKEN")) and bool(
            env.get("FACEBOOK_PAGE_ID")
        )
        if has_facebook_page:
            return []
        return [
            "facebook: require FACEBOOK_PAGE_ACCESS_TOKEN and FACEBOOK_PAGE_ID"
        ]

    if target != "x":
        return []

    has_buffer_x = bool(env.get("BUFFER_API_KEY")) and bool(env.get("BUFFER_X_CHANNEL_ID"))
    has_direct_x = all(
        env.get(name)
        for name in ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"]
    )
    if has_buffer_x or has_direct_x:
        return []
    return [
        "x: require BUFFER_API_KEY and BUFFER_X_CHANNEL_ID, or X_API_KEY, "
        "X_API_SECRET, X_ACCESS_TOKEN, and X_ACCESS_TOKEN_SECRET"
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate GitHub Actions secrets.")
    parser.add_argument("--mode", default="ci", choices=["ci", "syndicate", "archive", "upstream"])
    parser.add_argument("--schema", default="config/secrets.schema.json")
    parser.add_argument(
        "--target",
        choices=[
            "x",
            "discord",
            "mastodon",
            "threads",
            "instagram",
            "facebook",
            "linkedin",
            "bluesky",
        ],
    )
    parser.add_argument(
        "--env-file",
        default=".env.local",
        help="Optional local env file to merge before process environment.",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    env = load_env_file(args.env_file)
    env.update(os.environ)
    result = validate_environment(args.mode, schema=load_schema(args.schema), env=env, target=args.target)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    elif result["valid"]:
        print(f"Secret validation passed for mode: {args.mode}")
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
