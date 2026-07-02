# X redundant feed archive path

The X feed archive path adds redundancy beside public HTTP snapshots and browser capture.

It tries public RSS/Atom-style sources first:

- RSSHub routes such as `/twitter/user/<handle>`
- Nitter-compatible RSS endpoints such as `https://xcancel.com/<handle>/rss`
- configured Nitter public instances from the repository variable `NITTER_BASE_URLS`

This path does not log in, use proxies, solve CAPTCHAs, read browser cookies, call private GraphQL endpoints, or claim a full historical export.

## GitHub Actions

Use the existing `Archive Registered Sources` workflow:

```bash
gh workflow run "Archive Registered Sources" \
  -f source_type=x \
  -f capture_backend=feed \
  -f dry_run=false \
  -f limit_sources=1 \
  -f commit_payloads=true \
  -f publish=false
```

For combined redundancy:

```bash
gh workflow run "Archive Registered Sources" \
  -f source_type=x \
  -f capture_backend=browser_and_feed \
  -f dry_run=false \
  -f limit_sources=1 \
  -f commit_payloads=true \
  -f publish=false \
  -f max_scrolls=3 \
  -f idle_rounds=3 \
  -f per_account_timeout=120
```

## Configuration

Repository variables:

- `X_FEED_PROVIDERS`: default `rsshub,nitter`
- `RSSHUB_BASE_URLS`: comma-separated RSSHub bases, default `https://rsshub.app`
- `NITTER_BASE_URLS`: comma-separated Nitter-compatible bases, default starts with `https://xcancel.com`
- `X_FEED_TIMEOUT`: default `30`
- `X_FEED_MAX_ITEMS`: default `25`
- `X_AUTH_SCRAPE_ENABLED`: default `false`

Output paths:

- raw provider payloads: `historical_archive_raw/x_feed/<yyyy-mm>/`
- normalized records: `historical_archive_normalized/x/<yyyy-mm>.jsonl`
- feed report: `conductor/x_feed_archive_report.json`

Set workflow input `newsboat_health_check=true` only when you want Actions to generate the same feed URL set and run `newsboat -x reload` as a provider-health check. Newsboat output is not used as the canonical archive parser.

## Account-cookie scraper stubs

`twscrape` and `Scweet` are not enabled by default because they require authorized X account cookies or account pools. The workflow reports `auth_scrape_disabled` unless `X_AUTH_SCRAPE_ENABLED=true` is deliberately set and operator-provided credentials are configured.

The implementation must not extract cookies from Chrome automatically. If Chrome-login capture is later used, it should be a separate, explicit operator step.

Feediverse is not an ingestion backend for this repo. It republishes RSS/Atom feeds to Mastodon and is documented only as a reference for feed templating and de-duplication.
