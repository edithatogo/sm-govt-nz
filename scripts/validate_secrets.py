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
    if target != "x":
        return []

    has_direct_x = all(
        env.get(name)
        for name in ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"]
    )
    has_zernio_x = bool(env.get("ZERNIO_API_KEY")) and _zernio_has_target(env, "x")
    if has_direct_x or has_zernio_x:
        return []
    return [
        "x: require X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, and "
        "X_ACCESS_TOKEN_SECRET, or ZERNIO_API_KEY with an x entry in "
        "ZERNIO_ACCOUNT_IDS_JSON/ZERNIO_ACCOUNT_IDS_X"
    ]


def _zernio_has_target(env: dict[str, str], target: str) -> bool:
    if env.get(f"ZERNIO_ACCOUNT_IDS_{target.upper()}"):
        return True

    mapping_json = env.get("ZERNIO_ACCOUNT_IDS_JSON")
    if not mapping_json:
        return False
    try:
        mapping = json.loads(mapping_json)
    except json.JSONDecodeError:
        return False
    values = mapping.get(target)
    if isinstance(values, str):
        return bool(values.strip())
    if isinstance(values, list):
        return any(str(value).strip() for value in values)
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate GitHub Actions secrets.")
    parser.add_argument("--mode", default="ci", choices=["ci", "syndicate", "archive", "upstream"])
    parser.add_argument("--schema", default="config/secrets.schema.json")
    parser.add_argument("--target", choices=["x", "discord", "mastodon", "threads", "linkedin"])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = validate_environment(args.mode, schema=load_schema(args.schema), target=args.target)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    elif result["valid"]:
        print(f"Secret validation passed for mode: {args.mode}")
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
