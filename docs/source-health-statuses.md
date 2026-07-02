# Source Health Statuses

Archive adapters must report one of the statuses defined in
`config/source_health_statuses.json`.

## Statuses
- `healthy`: the source was reachable and returned records or a valid empty
  result.
- `degraded`: the source is reachable but partial, stale, incomplete, or
  dependent on secondary archive coverage.
- `auth_required`: the source requires operator authentication, OAuth setup, or
  a provider token before capture can run.
- `rate_limited`: the source refused or delayed capture because of rate limits
  or quota pressure.
- `blocked`: source access is technically or policy blocked for the current
  adapter.
- `unavailable`: the endpoint is down, removed, or cannot be reached after
  bounded retry.

## Contract
- A blocked source must not stop other source captures.
- `auth_required`, `blocked`, and `unavailable` should be visible in source
  health reports.
- `degraded`, `rate_limited`, and `unavailable` can be retried by scheduled
  archive workflows.
- Health status must never alter outbound syndication state.

## Archive gap priorities

Archive gap reports classify non-success states into implementation priorities:

- `p1_existing_resources`: likely fixable by URL normalization, alternate public endpoints, bounded retry, or adapter changes.
- `p2_existing_system_needs_seed_input`: the ingest system exists, but an operator-authorized seed file is missing.
- `p3_needs_operator_or_platform_access`: official API, export, login, or provider access is required.
- `p4_larger_browser_or_access_project`: needs a separate browser/API/access project and must not attempt CAPTCHA, login bypass, cookie extraction, or hidden private API capture by default.
