# Bluesky Archive Setup

The Bluesky lane archives registered government Bluesky sources into the same
historical corpus used by RSS and website archive lanes.

## Hybrid ingestion model

- Realtime push: `.github/workflows/archive_push_events.yml`
- Realtime event types: `bluesky_realtime_event`, `atproto_realtime_event`
- Daily reconciliation: `.github/workflows/archive_bluesky_sources.yml`
- Public corpus release: monthly through `Publish Archives`

Realtime and daily archiving are source-capture mechanisms. They must not publish
extra Hugging Face or Zenodo releases.

## Daily reconciliation workflow

- Workflow: `.github/workflows/archive_bluesky_sources.yml`
- Schedule: daily at `14:17 UTC`
- Manual dispatch: supported through `workflow_dispatch`
- Script: `scripts/archive_registered_sources.py --platform bluesky`

The workflow writes archive outputs to:

- `historical_archive/`
- `historical_archive_normalized/`
- `historical_archive_raw/`
- `conductor/archive_state.json`
- `conductor/archive_source_health.json`

## Required GitHub secrets

- `BLUESKY_IDENTIFIER`
- `BLUESKY_APP_PASSWORD`

The workflow also exports `BSKY_IDENTIFIER` and `BSKY_APP_PASSWORD` aliases for
compatibility with existing Bluesky client code.

## Realtime bridge

Run an always-on AT Protocol firehose bridge outside GitHub Actions. The bridge
should filter `com.atproto.sync.subscribeRepos` events to known government DIDs
or handles and forward matching records to GitHub as repository-dispatch events.

Use `docs/hybrid-realtime-archive-setup.md` as the payload contract.
