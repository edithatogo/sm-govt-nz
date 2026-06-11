from scripts.validate_secrets import validate_environment


SCHEMA = {
    "modes": {
        "syndicate": {
            "required": [],
            "anyOf": [
                {"name": "discord", "vars": ["DISCORD_WEBHOOK_URL"]},
                {"name": "x", "vars": ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"]},
            ],
        },
        "upstream": {"required": ["GH_TOKEN"], "anyOf": []},
    },
    "jsonVars": [],
}


def test_validate_environment_accepts_satisfied_any_group() -> None:
    result = validate_environment(
        "syndicate",
        schema=SCHEMA,
        env={"DISCORD_WEBHOOK_URL": "https://example.test/webhook"},
    )

    assert result["valid"] is True
    assert result["satisfied_groups"] == ["discord"]


def test_validate_environment_accepts_direct_x_target_credentials() -> None:
    result = validate_environment(
        "syndicate",
        schema=SCHEMA,
        env={
            "X_API_KEY": "key",
            "X_API_SECRET": "secret",
            "X_ACCESS_TOKEN": "token",
            "X_ACCESS_TOKEN_SECRET": "token-secret",
        },
        target="x",
    )

    assert result["valid"] is True
    assert result["target_errors"] == []


def test_validate_environment_rejects_x_target_without_x_credentials() -> None:
    result = validate_environment(
        "syndicate",
        schema=SCHEMA,
        env={"DISCORD_WEBHOOK_URL": "https://example.test/webhook"},
        target="x",
    )

    assert result["valid"] is False
    assert result["target_errors"]


def test_validate_environment_rejects_missing_any_group() -> None:
    result = validate_environment("syndicate", schema=SCHEMA, env={})

    assert result["valid"] is False
    assert result["requires_one_of"] == ["discord", "x"]


def test_validate_environment_rejects_zernio_only_for_x_target() -> None:
    result = validate_environment(
        "syndicate",
        schema=SCHEMA,
        env={"ZERNIO_API_KEY": "key", "ZERNIO_ACCOUNT_IDS_JSON": '{"x":["acct"]}'},
        target="x",
    )

    assert result["valid"] is False
    assert result["target_errors"]


def test_validate_environment_requires_upstream_token() -> None:
    result = validate_environment("upstream", schema=SCHEMA, env={})

    assert result["valid"] is False
    assert result["missing_required"] == ["GH_TOKEN"]
