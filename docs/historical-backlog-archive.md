# Historical backlog archive orchestration

The `Archive Historical Backlog` workflow fans out bounded archive shards across
all registered public and manual-seed source groups:

- `rss`
- `json_feed`
- `bluesky`
- `youtube`
- `website_page`
- `threads`
- `facebook`
- `instagram`
- `linkedin`
- `x`

Each shard dispatches the existing `Archive Registered Sources` workflow with a
source type, offset, and limit. This keeps capture behavior centralized while
letting GitHub Actions run source-type batches in parallel.

The workflow covers sources that already have archive payloads and sources that
are added later. Already-captured records remain idempotent because normalized
record IDs are stable. Manual-seed platforms report missing seeds until lawful
operator-authorized seed files are added under `manual_archive_seeds/`.

External publication remains monthly and dynamically versioned. The backlog
orchestrator may dispatch an HF-only `Publish Archives` run for the current
`YYYY-MM` release version, but the existing monthly guard prevents duplicate
same-month external releases. Retrospective months are handled by `Publish
Retrospective Monthly Archive`, which selects the oldest unpublished month from
`conductor/monthly_release_plan.json`.

The canonical dataset slug remains `corpus-social-media-government-nz`; the
display title is `New Zealand Government Social Media Corpus/Archive`.
