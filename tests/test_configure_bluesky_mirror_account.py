from scripts.configure_bluesky_mirror_account import configure_account


def test_cli_configures_profile_and_provisions_secrets_without_posting() -> None:
    calls = []
    secrets = []
    did = "did:plc:yvqqqg4jgfcggmc2ez7iiukm"

    def transport(method, endpoint, payload, token):
        calls.append((method, endpoint, payload, bool(token)))
        if endpoint == "com.atproto.server.createSession":
            return {"did": did, "accessJwt": "jwt"}
        if endpoint.startswith("com.atproto.repo.getRecord"):
            return {
                "value": {
                    "$type": "app.bsky.actor.profile",
                    "avatar": {"ref": "preserved"},
                }
            }
        if endpoint == "com.atproto.server.createAppPassword":
            return {"password": "secret-app-password"}
        return {}

    report = configure_account(
        {
            "mirror_id": "electoral-commission",
            "handle": "elect-com-nz-arc.bsky.social",
            "display_name": "Electoral Commission Archive Mirror",
            "environment": "bluesky-mirror-electoral-commission",
        },
        "primary-password",
        did,
        description="Unofficial automated archive mirror.",
        transport=transport,
        secret_setter=lambda environment, name, value: secrets.append(
            (environment, name, value)
        ),
    )

    put_record = next(call for call in calls if call[1] == "com.atproto.repo.putRecord")
    record = put_record[2]["record"]
    assert record["avatar"] == {"ref": "preserved"}
    assert record["labels"]["values"] == [{"val": "bot"}]
    assert all("feed.post" not in call[1] for call in calls)
    assert [name for _, name, _ in secrets] == [
        "BLUESKY_HANDLE",
        "BLUESKY_APP_PASSWORD",
    ]
    assert report["posting_performed"] is False
    assert report["secret_values_recorded"] is False
    assert "secret-app-password" not in str(report)
    assert "primary-password" not in str(report)
