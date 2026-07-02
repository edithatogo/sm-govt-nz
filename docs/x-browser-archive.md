# X browser archive path

The X browser archive path uses SeleniumBase Stealthy Playwright Mode:

- SeleniumBase starts a hardened Chromium session.
- Playwright attaches with `connect_over_cdp()`.
- Local and GitHub Actions runs capture public rendered X profile/timeline content.

This path is the primary best-effort source for X when official API credits are unavailable. It does not log in, use proxies, solve CAPTCHAs, call private GraphQL endpoints, or bypass explicit access controls.

## Local proof commands

One-source proof:

```bash
python -m scripts.archive_x_browser --limit-sources 1 --max-scrolls 3 --per-account-timeout 120
```

Full local browser run:

```bash
python -m scripts.archive_x_browser --max-scrolls 25 --idle-rounds 3 --per-account-timeout 120
```

Fixture smoke test without live X:

```bash
python -m scripts.archive_x_browser --fixture-html tests/fixtures/x_timeline_sample.html --limit-sources 1
```

## GitHub Actions

Use the existing `Archive Registered Sources` workflow:

```bash
gh workflow run "Archive Registered Sources" \
  -f source_type=x \
  -f capture_backend=browser \
  -f dry_run=false \
  -f limit_sources=1 \
  -f commit_payloads=true \
  -f publish=false \
  -f max_scrolls=3 \
  -f idle_rounds=3 \
  -f per_account_timeout=120
```

For full X browser archival, set `limit_sources=0` and `max_scrolls=25`.

The workflow runs headful Chromium inside Xvfb on Ubuntu.

Use `capture_backend=browser_and_feed` when you want RSSHub/Nitter-compatible feed capture to run before the browser fallback in the same archive job.
