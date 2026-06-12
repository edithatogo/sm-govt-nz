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
