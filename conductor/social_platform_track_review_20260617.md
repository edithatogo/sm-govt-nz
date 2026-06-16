# Courts of New Zealand Social Platform Track Review - 2026-06-17

This review maps existing conductor tracks against the current runtime config.
It distinguishes account/setup work from live scheduled posting.

## Runtime Matrix

| Platform | Track coverage | Runtime status | Next track/action |
| --- | --- | --- | --- |
| Bluesky source | `courts_nz_mirror_20260611`, `courts_nz_multisource_archive_20260612` | Active source: `courtsofnz.bsky.social` | Continue archive capture and source health monitoring. |
| Bluesky mirror | `courts_nz_bluesky_mirror_20260612`, `courts_nz_bluesky_launch_ops_20260613` | Active target: `bluesky.enabled=true` | Continue new-forward mirroring. |
| Bluesky historical replay | `courts_nz_bluesky_archive_replay_20260613` | In progress: X replay remaining | Continue bounded manual Archive Replay runs. Top-level status corrected from complete to in progress. |
| X/Twitter mirror | Core adapter exists; no dedicated completion track existed | Not live: `x.enabled=false`, not in `syndicate_to` | New track: `courts_nz_x_twitter_launch_route_20260617`. |
| Threads mirror | `courts_nz_threads_mirror_20260612`, `courts_nz_threads_api_credentials_20260613`, `courts_nz_threads_adapter_launch_20260613` | Active target: `threads.enabled=true`, one delivery recorded | Continue new-forward mirroring; historical replay remains deferred. |
| Threads historical replay | `courts_nz_threads_historical_replay_policy_20260613` | Deferred by policy | No backlog replay unless a future explicit review accepts current-feed archive noise. |
| Instagram mirror | `courts_nz_instagram_meta_api_20260613` | Not live in runtime config despite older launch notes | New reconciliation track: `courts_nz_instagram_launch_reconciliation_20260617`. |
| Facebook Page mirror | `courts_nz_facebook_meta_api_20260613` | Blocked: dedicated Page identity not confirmed | Continue existing Facebook track after Page identity exists. |
| LinkedIn source | `courts_nz_multisource_archive_20260612` | Paused/source-only | Remains archive-only pending approved seed/access; no posting. |
| RSS/website | `courts_nz_multisource_archive_20260612` | Scheduled archive capture active | Continue source-health monitoring. |
| Judgments email | `courts_nz_multisource_archive_20260612` | Email bridge scaffold exists; subscription/address confirmation remains open | Resolve the dedicated subscription address lane or keep Pipedream fallback documented. |
| Hugging Face dataset | `archiver_zenodo_20260610`, `courts_nz_multisource_archive_20260612` | Published once; cadence needs explicit policy | New cadence track: `courts_nz_archive_publication_cadence_20260617`. |
| Zenodo | `archiver_zenodo_20260610`, `courts_nz_multisource_archive_20260612` | v1 DOI published; future snapshots need cadence | New cadence track covers episodic snapshots. |
| Government registry expansion | `govt_registry_20260614` | Open/deferred beyond seed phases | Continue after Courts platform lanes stabilize. |

## Current Config Summary

- `monitored_accounts[0].syndicate_to`: `bluesky`, `threads`.
- Enabled targets: Bluesky and Threads.
- Disabled outbound targets: X/Twitter, Instagram, Facebook, Mastodon, Discord,
  LinkedIn, unified registry feed.
- Archive replay to Bluesky is enabled for recovered X archive records.
- Threads, Instagram, and Facebook archive replay remain disabled.

## Review Findings

1. Bluesky and Threads are the only live scheduled outbound targets.
2. X/Twitter needs a dedicated launch-route track because prior work left the
   runtime target disabled.
3. Instagram has stale completion notes relative to runtime config and needs
   reconciliation before being described as live.
4. Facebook already has a track and remains blocked on a dedicated Page identity.
5. Dataset publication exists, but the automatic versus manual external publish
   cadence needs an explicit track-level decision.
