# Credentialed platform access readiness

This repository defaults to public, keyless, or operator-authorized seed capture. Credentialed live API capture is optional and must be deliberately enabled per platform.

## Machine-readable state

The readiness workflow writes:

- `conductor/credentialed_platform_access_report.json`
- `conductor/credentialed_platform_access_summary.md`

The report distinguishes three states:

- `api_disabled_manual_seed_path` or `api_disabled_public_or_seed_path`: report-only; the platform remains registered and monitored, but live API capture is disabled.
- `api_enabled_missing_secret`: actionable; the live gate is enabled but required secrets are absent.
- `api_enabled_ready`: the live gate is enabled and one required secret set is present.

Disabled credentialed paths must not create blocker issues. Missing manual seeds remain tracked by the manual seed reports and archive reports.

## Activation gates

| Platform | Gate | Required secrets | Default path |
| --- | --- | --- | --- |
| Threads | `THREADS_API_CAPTURE_ENABLED=true` | `THREADS_ACCESS_TOKEN` | authorized seed files |
| X official API | `X_API_CAPTURE_ENABLED=true` | `X_BEARER_TOKEN` or OAuth 1.0a secret set | public snapshot/feed, then authorized seed |
| LinkedIn | `LINKEDIN_API_CAPTURE_ENABLED=true` | `LINKEDIN_ACCESS_TOKEN` | authorized seed files |
| Facebook | `FACEBOOK_GRAPH_CAPTURE_ENABLED=true` | `FACEBOOK_PAGE_ACCESS_TOKEN` or `META_GRAPH_ACCESS_TOKEN` | authorized seed files |
| Instagram | `INSTAGRAM_GRAPH_CAPTURE_ENABLED=true` | `INSTAGRAM_ACCESS_TOKEN` or `META_GRAPH_ACCESS_TOKEN` | authorized seed files |

## Issue policy

GitHub issues are only created for actionable automation faults:

- a live API gate is enabled and required secrets are missing;
- a live API gate is enabled and the platform returns permission, quota, billing, or configuration errors;
- a seed file exists but is invalid or empty.

Expected zero-input states, including `manual_seed_missing`, are report-only coverage gaps.

## Operator rule

Do not describe a registered credentialed-platform account as archived until records exist in `historical_archive_normalized/<platform>/`. Registered sources with no seed or disabled API gate are only registered and monitored.
