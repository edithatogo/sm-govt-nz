# Zernio CLI Integration

This project can use `zernio-cli` for outbound syndication when Zernio-connected
social accounts are available.

## What Zernio Replaces

Use Zernio for outbound posting to connected accounts:

```powershell
zernio accounts:list --pretty
zernio posts:create --text "Update text" --accounts <accountId>
```

In GitHub Actions, configure:

- `ZERNIO_API_KEY`
- `ZERNIO_ACCOUNT_IDS_JSON`

Example account mapping:

```json
{
  "x": ["acct_x"],
  "linkedin": ["acct_linkedin"],
  "threads": ["acct_threads"]
}
```

The runner will prefer Zernio for a platform when that platform has mapped
account IDs. Direct platform-specific adapters remain as fallback paths.

## What Zernio Does Not Replace

Zernio CLI does not currently provide a general public-source ingestion command
for arbitrary government agency profiles or websites. Keep source ingestion in
platform/source adapters such as RSS, AT Protocol, Mastodon, YouTube, and other
API-specific readers. Keep archival and backfill scripts local because they
produce repository-owned evidence artifacts.
