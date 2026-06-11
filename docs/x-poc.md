# X Proof of Concept

The X proof of concept has two supported outbound paths.

## Preferred: Zernio

Use Zernio when the X account is connected in Zernio:

```json
{
  "x": ["acct_x"]
}
```

Configure GitHub secrets:

- `ZERNIO_API_KEY`
- `ZERNIO_ACCOUNT_IDS_JSON`

## Direct fallback: Tweepy

Use Tweepy when posting directly through X API v2. The app must have write
permissions, and the access token must be regenerated after write permissions
are enabled.

Configure GitHub secrets:

- `X_API_KEY`
- `X_API_SECRET`
- `X_ACCESS_TOKEN`
- `X_ACCESS_TOKEN_SECRET`

The runner uses OAuth 1.0a user context through `tweepy.Client.create_tweet`.

## Local validation

```powershell
python scripts/validate_secrets.py --mode syndicate --json
pytest -q tests/test_syndication.py
```
