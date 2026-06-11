# X Proof Of Concept

The X proof of concept uses direct X API v2 posting through Tweepy.

Use Tweepy when posting directly through X API v2. The app must have write
permissions, and the access token must be regenerated after write permissions
are enabled.

Configure GitHub secrets:

- `X_API_KEY`
- `X_API_SECRET`
- `X_ACCESS_TOKEN`
- `X_ACCESS_TOKEN_SECRET`

The runner uses OAuth 1.0a user context through `tweepy.Client.create_tweet`.

## Archived: Zernio

Zernio is no longer part of the active MVP launch path. Historical integration
notes remain in `docs/zernio.md`, but the syndication workflow does not install
or prefer `zernio-cli`.

## Local validation

```powershell
python scripts/validate_secrets.py --mode syndicate --json
pytest -q tests/test_syndication.py
```
