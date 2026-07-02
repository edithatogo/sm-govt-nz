# Website browser fallback archive

The normal website lane uses bounded public HTTP requests first. This fallback lane is only for public website pages that remain eligible after HTTP capture and failure triage.

## Eligibility

Browser fallback is intended for these HTTP failure states:

- `capture_blocked`
- `method_not_allowed`
- `not_acceptable`
- `network_error`
- `network_timeout`

These states are not browser fallback defaults:

- `dns_failed`: verify or retire the URL first.
- `not_found`: verify or retire the URL first.
- `tls_failed`: review TLS or alternate URL first.

The runner reads `conductor/website_archive_failure_triage_report.json` and selects only matching `website_page` sources unless `--include-without-triage` is deliberately provided for local fixture tests.

## Capture outputs

Raw browser evidence is written to:

- `historical_archive_raw/website_browser/<yyyy-mm>/<record_id>.json`
- optional screenshots under `historical_archive_raw/website_browser/<yyyy-mm>/<record_id>.png`

Normalized text is appended to:

- `historical_archive_normalized/website/<yyyy-mm>.jsonl`

Browser fallback records use:

- `record_id`: `website_browser:<stable_id>`
- `source_kind`: `website_browser_fallback`
- `extraction_method`: `playwright_public_browser_fallback`

## Guardrails

The workflow is public and keyless only:

- no login;
- no CAPTCHA solving;
- no proxies;
- no credential bypass;
- no private API calls.

CAPTCHA, anti-bot challenge, access denied, and login-required pages are recorded as statuses and raw evidence. They are not bypassed.

## GitHub Actions

Manual shard example:

```bash
gh workflow run "Archive Website Browser Fallback" \
  -f dry_run=false \
  -f limit_sources=10 \
  -f offset_sources=0 \
  -f commit_payloads=true
```

External publication remains monthly guarded. Set `publish=true` only when a monthly release should be attempted; later same-month runs should remain report/artifact or commit-only.
