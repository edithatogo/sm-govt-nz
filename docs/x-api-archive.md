# X API archive path

The repository supports two X capture paths:

- primary path: unauthenticated public HTTP profile snapshots
- optional enhancement: official X API post capture when credits/billing are available

## Default state

Registered X accounts are captured through public HTTP snapshots by default in GitHub Actions. They remain `manual_seed_missing` only when both public snapshots and official API capture are disabled and no authorized seed exists.

Additional inputs can improve coverage:

- an operator-authorized seed file under `manual_archive_seeds/x/`
- `X_API_CAPTURE_ENABLED=true` configured as a repository variable
- valid X API credentials configured as repository secrets

Official X API access is usage-billed. A stored secret alone must not cause archive runs to make paid API calls.

## Required GitHub configuration

Set this repository variable only when paid/credited X API usage is approved:

- `X_API_CAPTURE_ENABLED=true`

Set either a bearer token:

- `X_BEARER_TOKEN`

Or OAuth 1.0a credentials:

- `X_API_KEY`
- `X_API_SECRET`
- `X_ACCESS_TOKEN`
- `X_ACCESS_TOKEN_SECRET`

The workflow defaults to `https://api.x.com/2`. Override with repository variable `X_API_BASE_URL` only for testing or if X changes the API host.

## Capture behavior

When enabled, `Archive Registered Sources` resolves each account handle to a user ID, then calls the official user timeline endpoint for recent posts. It writes:

- raw payloads under `historical_archive_raw/x/<yyyy-mm>/`
- normalized records under `historical_archive_normalized/x/<yyyy-mm>.jsonl`
- per-source status in `conductor/x_archive_report.json`

When disabled, the workflow does not call X. If an authorized seed exists, it archives the seed. If no seed exists, it reports `manual_seed_missing`.

## Public HTTP snapshot primary path

The repository uses conservative public HTTP snapshots as the primary ongoing X archival path:

- `X_PUBLIC_SNAPSHOT_ENABLED=true`

This path uses unauthenticated public HTTP requests only. It does not log in, use proxies, bypass anti-bot controls, call private GraphQL endpoints, or attempt to reconstruct full timelines. It stores the accessible public profile page HTML and normalized profile-snapshot metadata as provenance evidence.

Snapshot output is intentionally distinct from post-level API or seed records:

- raw snapshots: `historical_archive_raw/x_public_snapshot/<yyyy-mm>/`
- normalized snapshot records: `historical_archive_normalized/x/<yyyy-mm>.jsonl`
- record IDs: `x_public_snapshot:<stable_id>`
- status: `public_snapshot_captured`, `public_snapshot_already_captured`, or the relevant blocked/error status

Use official X API capture only as an optional enhancement when credits/billing are available. Public HTTP snapshots remain the default source for X.

## Cost and safety controls

The `max_x_posts` workflow input limits recent posts requested per account. The default is `25`, capped to the X API endpoint range of `5` to `100`.

Use dry-runs before enabling live capture:

```bash
gh workflow run "Archive Registered Sources" -f source_type=x -f dry_run=true
```

After enabling `X_API_CAPTURE_ENABLED`, run a small live shard first:

```bash
gh workflow run "Archive Registered Sources" -f source_type=x -f dry_run=false -f limit_sources=1 -f commit_payloads=true -f max_x_posts=5
```

Only expand to all X sources after the small shard report shows `captured`, `already_captured`, or `no_records` without `x_billing_required`, `x_permission_error`, or `rate_limited`.

To run the public HTTP snapshot source without calling the X API:

```bash
gh variable set X_API_CAPTURE_ENABLED --body false
gh variable set X_PUBLIC_SNAPSHOT_ENABLED --body true
gh workflow run "Archive Registered Sources" -f source_type=x -f dry_run=false -f limit_sources=1 -f commit_payloads=true
```
