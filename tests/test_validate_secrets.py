from scripts.validate_secrets import load_env_file, validate_environment


SCHEMA = {
    "modes": {
        "syndicate": {
            "required": [],
            "anyOf": [
                {"name": "buffer", "vars": ["BUFFER_API_KEY", "BUFFER_X_CHANNEL_ID"]},
                {"name": "discord", "vars": ["DISCORD_WEBHOOK_URL"]},
                {"name": "x", "vars": ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"]},
                {"name": "bluesky", "vars": ["BLUESKY_MIRROR_HANDLE", "BLUESKY_MIRROR_APP_PASSWORD"]},
                {"name": "threads", "vars": ["THREADS_ACCESS_TOKEN", "THREADS_USER_ID"]},
                {"name": "threads legacy alias", "vars": ["THREADS_ACCESS_TOKEN", "THREADS_MIRROR_ACCOUNT_ID"]},
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


def test_validate_environment_accepts_buffer_x_target_credentials() -> None:
    result = validate_environment(
        "syndicate",
        schema=SCHEMA,
        env={"BUFFER_API_KEY": "key", "BUFFER_X_CHANNEL_ID": "channel"},
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


def test_validate_environment_accepts_bluesky_target_credentials() -> None:
    result = validate_environment(
        "syndicate",
        schema=SCHEMA,
        env={
            "BLUESKY_MIRROR_HANDLE": "mirnzcourts.bsky.social",
            "BLUESKY_MIRROR_APP_PASSWORD": "app-password",
        },
        target="bluesky",
    )

    assert result["valid"] is True
    assert result["target_errors"] == []


def test_validate_environment_rejects_bluesky_target_without_credentials() -> None:
    result = validate_environment(
        "syndicate",
        schema=SCHEMA,
        env={"DISCORD_WEBHOOK_URL": "https://example.test/webhook"},
        target="bluesky",
    )

    assert result["valid"] is False
    assert result["target_errors"]


def test_validate_environment_accepts_threads_target_credentials() -> None:
    result = validate_environment(
        "syndicate",
        schema=SCHEMA,
        env={
            "THREADS_ACCESS_TOKEN": "token",
            "THREADS_USER_ID": "threads-user",
        },
        target="threads",
    )

    assert result["valid"] is True
    assert result["target_errors"] == []


def test_validate_environment_accepts_threads_legacy_account_id_alias() -> None:
    result = validate_environment(
        "syndicate",
        schema=SCHEMA,
        env={
            "THREADS_ACCESS_TOKEN": "token",
            "THREADS_MIRROR_ACCOUNT_ID": "threads-user",
        },
        target="threads",
    )

    assert result["valid"] is True
    assert result["target_errors"] == []


def test_validate_environment_rejects_threads_target_without_credentials() -> None:
    result = validate_environment(
        "syndicate",
        schema=SCHEMA,
        env={"THREADS_ACCESS_TOKEN": "token"},
        target="threads",
    )

    assert result["valid"] is False
    assert result["target_errors"]


def test_validate_environment_rejects_missing_any_group() -> None:
    result = validate_environment("syndicate", schema=SCHEMA, env={})

    assert result["valid"] is False
    assert result["requires_one_of"] == [
        "buffer",
        "discord",
        "x",
        "bluesky",
        "threads",
        "threads legacy alias",
    ]


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


def test_load_env_file_reads_simple_key_values(tmp_path) -> None:
    env_file = tmp_path / ".env.local"
    env_file.write_text(
        """
        # local only
        BUFFER_API_KEY="buffer-key"
        BUFFER_X_CHANNEL_ID='channel-x'
        EMPTY=
        """,
        encoding="utf-8",
    )

    assert load_env_file(env_file) == {
        "BUFFER_API_KEY": "buffer-key",
        "BUFFER_X_CHANNEL_ID": "channel-x",
        "EMPTY": "",
    }


def test_load_env_file_ignores_empty_path() -> None:
    assert load_env_file("") == {}
