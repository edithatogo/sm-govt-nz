from scripts.validate_secrets import validate_environment


SCHEMA = {
    "modes": {
        "syndicate": {
            "required": [],
            "anyOf": [
                {"name": "zernio", "vars": ["ZERNIO_API_KEY", "ZERNIO_ACCOUNT_IDS_JSON"]},
                {"name": "discord", "vars": ["DISCORD_WEBHOOK_URL"]},
            ],
        },
        "upstream": {"required": ["GH_TOKEN"], "anyOf": []},
    },
    "jsonVars": ["ZERNIO_ACCOUNT_IDS_JSON"],
}


def test_validate_environment_accepts_satisfied_any_group() -> None:
    result = validate_environment(
        "syndicate",
        schema=SCHEMA,
        env={"ZERNIO_API_KEY": "key", "ZERNIO_ACCOUNT_IDS_JSON": '{"x":["acct"]}'},
    )

    assert result["valid"] is True
    assert result["satisfied_groups"] == ["zernio"]


def test_validate_environment_rejects_missing_any_group() -> None:
    result = validate_environment("syndicate", schema=SCHEMA, env={})

    assert result["valid"] is False
    assert result["requires_one_of"] == ["zernio", "discord"]


def test_validate_environment_reports_invalid_json_secret() -> None:
    result = validate_environment(
        "syndicate",
        schema=SCHEMA,
        env={"ZERNIO_API_KEY": "key", "ZERNIO_ACCOUNT_IDS_JSON": "not-json"},
    )

    assert result["valid"] is False
    assert result["json_errors"]


def test_validate_environment_requires_upstream_token() -> None:
    result = validate_environment("upstream", schema=SCHEMA, env={})

    assert result["valid"] is False
    assert result["missing_required"] == ["GH_TOKEN"]
