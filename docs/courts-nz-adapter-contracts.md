# Courts of New Zealand Adapter Contracts

The machine-readable source contracts are in `config/courts-of-nz_sources.json`.
This document is the Phase 1 review summary for implementers.

## Global Contract
- This track is archive-only.
- Archive adapters must not advance `conductor/state.json` or enqueue outbound
  posts.
- Raw records must be written before normalization when source payloads are
  available.
- Normalized records must preserve source platform, account/feed, source URL,
  captured timestamp, original timestamp when available, canonical URL, content
  hash, raw path, media references, and extraction method.
- Failed sources must report health and must not block healthy sources.

## Bluesky
- Contract ID: `courts-nz-bluesky`
- Access: public AT Protocol.
- Auth: none.
- Status: `healthy`.
- Dedupe: AT URI, canonical URL, content hash.
- Raw path: `historical_archive_raw/bluesky/{yyyy_mm}/{record_id}.json`
- Normalized path: `historical_archive_normalized/bluesky/{yyyy_mm}.jsonl`
- Failure modes: `rate_limited`, `network_error`, `schema_changed`.
- Guardrail: archive backfills must not advance outbound syndication state.

## LinkedIn
- Contract ID: `courts-nz-linkedin`
- Access: approved LinkedIn Community Management / Posts API if available;
  otherwise user-authorized browser capture or manual seed.
- Auth: operator-authorized.
- Status: `auth_required`.
- Dedupe: LinkedIn post URL, canonical URL, content hash.
- Raw path: `historical_archive_raw/linkedin/{yyyy_mm}/{record_id}.json`
- Normalized path: `historical_archive_normalized/linkedin/{yyyy_mm}.jsonl`
- Failure modes: `auth_required`, `rate_limited`, `blocked`,
  `schema_changed`.
- Guardrail: LinkedIn records are evidence inputs only and must never be
  reposted by this track.

## X Historical Archive
- Contract ID: `courts-nz-x-archive`
- Access: account-owner export if available; otherwise Internet Archive CDX over
  legacy Twitter URLs, with X URLs as supplementary coverage.
- Auth: only required for bounded browser gap capture.
- Status: `degraded`.
- Historical cutoff: 23 March 2025.
- Dedupe: tweet ID, canonical URL, content hash.
- Raw path: `historical_archive_raw/x/{yyyy_mm}/{record_id}.json`
- Normalized path: `historical_archive_normalized/x/{yyyy_mm}.jsonl`
- Failure modes: `auth_required`, `blocked`, `unavailable`,
  `incomplete_archive`.
- Guardrail: X archive records are historical only and must not enter any live
  posting queue.

## RSS and Website
- Contract ID: `courts-nz-rss-website`
- Access: public RSS and bounded HTML fetches.
- Auth: none.
- Status: `healthy`.
- Dedupe: feed entry ID, canonical URL, content hash.
- Raw path: `historical_archive_raw/rss/{yyyy_mm}/{record_id}.json`
- Normalized path: `historical_archive_normalized/rss/{yyyy_mm}.jsonl`
- Failure modes: `feed_unavailable`, `network_error`, `html_changed`.
- Guardrail: RSS and website records may enrich the corpus but must not alter
  outbound syndication cursors.

## Email Judgments Subscription
- Contract ID: `courts-nz-email-judgments`
- Access: Cloudflare Email Routing Worker.
- Auth: GitHub dispatch token.
- Status: `auth_required`.
- Dedupe: message ID, canonical URL, content hash.
- Raw path: `historical_archive_raw/email/{yyyy_mm}/{record_id}.eml`
- Normalized path: `historical_archive_normalized/email/{yyyy_mm}.jsonl`
- Failure modes: `auth_required`, `dispatch_failed`, `malformed_email`,
  `provider_outage`.
- Guardrail: email notifications are corpus inputs only and must never create
  outbound posts directly.

## Dataset Outputs
- Hugging Face: normalized JSONL, normalized Parquet, manifest, dataset card.
- Zenodo: release snapshot, manifest, checksums, citation metadata.

## Phase Review Checklist
- Each adapter has an explicit input contract and auth mode.
- Each adapter has raw and normalized output paths.
- Each adapter has dedupe keys and source health failure modes.
- Each adapter has an archive-only guarantee.
- Each future outbound syndication account must be created as a separate track.
