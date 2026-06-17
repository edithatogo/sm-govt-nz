# Courts of New Zealand Social Platform Track Review - 2026-06-17

This review maps existing conductor tracks against the current runtime config.
It distinguishes account/setup work from live scheduled posting.

## Runtime Matrix

| Platform | Track coverage | Runtime status | Next track/action |
| --- | --- | --- | --- |
| Bluesky source | `courts_nz_mirror_20260611`, `courts_nz_multisource_archive_20260612` | Active source: `courtsofnz.bsky.social` | Continue archive capture and source health monitoring. |
| Bluesky mirror | `courts_nz_bluesky_mirror_20260612`, `courts_nz_bluesky_launch_ops_20260613` | Active target: `bluesky.enabled=true` | Continue new-forward mirroring. |
| Bluesky historical replay | `courts_nz_bluesky_archive_replay_20260613` | In progress: X replay remaining | Continue bounded manual Archive Replay runs. Top-level status corrected from complete to in progress. |
| X/Twitter mirror | `courts_nz_x_twitter_launch_route_20260617` | Buffer route active: `x.enabled=true`, `x` in `syndicate_to`, max 1 post/run, Buffer send status `sent` | Resolve public X status URL verification; Buffer does not expose final provider URL in current lookup output. |
| Threads mirror | `courts_nz_threads_mirror_20260612`, `courts_nz_threads_api_credentials_20260613`, `courts_nz_threads_adapter_launch_20260613` | Active target: `threads.enabled=true`, one delivery recorded | Continue new-forward mirroring; historical replay remains deferred. |
| Threads historical replay | `courts_nz_threads_historical_replay_policy_20260613` | Deferred by policy | No backlog replay unless a future explicit review accepts current-feed archive noise. |
| Instagram mirror | `courts_nz_instagram_meta_api_20260613`, `courts_nz_instagram_launch_reconciliation_20260617` | Deferred: disabled in runtime config, no Instagram delivery state, missing Instagram Graph API secrets | Add `INSTAGRAM_ACCESS_TOKEN` and `INSTAGRAM_USER_ID`, run non-posting probe for `@mirnzcourts`, then review dry-run before enabling. |
| Facebook Page mirror | `courts_nz_facebook_meta_api_20260613` | Blocked: dedicated Page identity not confirmed | Continue existing Facebook track after Page identity exists. |
| LinkedIn source | `courts_nz_multisource_archive_20260612` | Paused/source-only | Remains archive-only pending approved seed/access; no posting. |
| RSS/website | `courts_nz_multisource_archive_20260612` | Scheduled archive capture active | Continue source-health monitoring. |
| Judgments email | `courts_nz_multisource_archive_20260612` | Email bridge scaffold exists; subscription/address confirmation remains open | Resolve the dedicated subscription address lane or keep Pipedream fallback documented. |
| Hugging Face dataset | `archiver_zenodo_20260610`, `courts_nz_multisource_archive_20260612` | Published once; cadence needs explicit policy | New cadence track: `courts_nz_archive_publication_cadence_20260617`. |
| Zenodo | `archiver_zenodo_20260610`, `courts_nz_multisource_archive_20260612` | v1 DOI published; future snapshots need cadence | New cadence track covers episodic snapshots. |
| Government registry expansion | `govt_registry_20260614` | Open/deferred beyond seed phases | Continue after Courts platform lanes stabilize. |

## Current Config Summary

- `monitored_accounts[0].syndicate_to`: `bluesky`, `threads`, `x`.
- Enabled targets: Bluesky, Threads, and X/Twitter through Buffer.
- Disabled outbound targets: Instagram, Facebook, Mastodon, Discord,
  LinkedIn, unified registry feed.
- Archive replay to Bluesky is enabled for recovered X archive records.
- Threads, Instagram, and Facebook archive replay remain disabled.

## Review Findings

1. Bluesky and Threads are the only live scheduled outbound targets.
2. X/Twitter now uses the Buffer launch route. Buffer validation, controlled
   live send, delivery-state commit, and first scheduled run passed; public X
   status URL verification remains open because Buffer did not expose the final
   provider URL.
3. Instagram stale completion notes have been reconciled. Instagram is deferred,
   not live, until Graph API credentials are configured and the dedicated
   `@mirnzcourts` account is verified without posting.
4. Facebook already has a track and remains blocked on a dedicated Page identity.
5. Dataset publication exists, but the automatic versus manual external publish
   cadence needs an explicit track-level decision.
