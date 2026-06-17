# Project Tracks

This file tracks all major tracks for the project. Each track has its own detailed plan in its respective folder.

---

## [x] Track: Build core syndication engine and public transparency website (MVP)
*Link: [./tracks/core_syndicator_20260610/](./tracks/core_syndicator_20260610/)*

## [x] Track: Map NZ agencies social media profiles, gap analysis registry, and self-improving agent workflow
*Link: [./tracks/agency_mapping_20260610/](./tracks/agency_mapping_20260610/)*

## [x] Track: Create post archiver, edit-history tracker, and Zenodo/Hugging Face publisher
*Link: [./tracks/archiver_zenodo_20260610/](./tracks/archiver_zenodo_20260610/)*

## [x] Track: Setup platform developer onboarding, secrets setup, and bleeding-edge GitHub integrations
*Link: [./tracks/github_integrations_20260610/](./tracks/github_integrations_20260610/)*

## [x] Track: Prioritize Courts of New Zealand mirror synchronization
*Link: [./tracks/courts_nz_mirror_20260611/](./tracks/courts_nz_mirror_20260611/)*

## [ ] Track: Archive Courts of New Zealand multi-source records and publish datasets
*Link: [./tracks/courts_nz_multisource_archive_20260612/](./tracks/courts_nz_multisource_archive_20260612/)*

## [x] Track: Establish Courts of New Zealand Bluesky mirror account
*Link: [./tracks/courts_nz_bluesky_mirror_20260612/](./tracks/courts_nz_bluesky_mirror_20260612/)*

## [x] Track: Establish Courts of New Zealand Threads mirror account
*Link: [./tracks/courts_nz_threads_mirror_20260612/](./tracks/courts_nz_threads_mirror_20260612/)*

## [x] Track: Complete Courts of New Zealand Bluesky profile evidence and identity archive
*Link: [./tracks/courts_nz_bluesky_profile_archive_20260613/](./tracks/courts_nz_bluesky_profile_archive_20260613/)*

## [~] Track: Complete Courts of New Zealand Bluesky archive replay and manifest telemetry
*Link: [./tracks/courts_nz_bluesky_archive_replay_20260613/](./tracks/courts_nz_bluesky_archive_replay_20260613/)*
- Remaining work: continue bounded X archive replay runs to the Bluesky mirror.

## [x] Track: Harden Courts of New Zealand Bluesky mirror launch operations
*Link: [./tracks/courts_nz_bluesky_launch_ops_20260613/](./tracks/courts_nz_bluesky_launch_ops_20260613/)*

## [x] Track: Implement Courts of New Zealand Threads API credentials and validation
*Link: [./tracks/courts_nz_threads_api_credentials_20260613/](./tracks/courts_nz_threads_api_credentials_20260613/)*

## [x] Track: Implement Courts of New Zealand Threads adapter and controlled launch
*Link: [./tracks/courts_nz_threads_adapter_launch_20260613/](./tracks/courts_nz_threads_adapter_launch_20260613/)*

## [x] Track: Decide Courts of New Zealand Threads historical replay policy
*Link: [./tracks/courts_nz_threads_historical_replay_policy_20260613/](./tracks/courts_nz_threads_historical_replay_policy_20260613/)*

## [~] Track: Implement Courts of New Zealand Instagram mirror via Meta APIs
*Link: [./tracks/courts_nz_instagram_meta_api_20260613/](./tracks/courts_nz_instagram_meta_api_20260613/)*
- Superseded launch notes reconciled: Instagram remains disabled until Graph API
  credentials are configured and `@mirnzcourts` is verified by non-posting probe.

## [x] Track: Reconcile Courts of New Zealand Instagram launch runtime state
*Link: [./tracks/courts_nz_instagram_launch_reconciliation_20260617/](./tracks/courts_nz_instagram_launch_reconciliation_20260617/)*
- Outcome: deferred; missing `INSTAGRAM_ACCESS_TOKEN` and `INSTAGRAM_USER_ID`.

## [~] Track: Select and launch Courts of New Zealand X/Twitter mirror route
*Link: [./tracks/courts_nz_x_twitter_launch_route_20260617/](./tracks/courts_nz_x_twitter_launch_route_20260617/)*
- Buffer route selected and configured; pending current-head validation,
  controlled live post, public URL verification, and first scheduled run review.

## [ ] Track: Implement Courts of New Zealand Facebook Page mirror via Meta APIs
*Link: [./tracks/courts_nz_facebook_meta_api_20260613/](./tracks/courts_nz_facebook_meta_api_20260613/)*

## [ ] Track: Define Courts of New Zealand archive publication cadence
*Link: [./tracks/courts_nz_archive_publication_cadence_20260617/](./tracks/courts_nz_archive_publication_cadence_20260617/)*

## [~] Track: NZ Government Social Media Registry � agencies, political parties, MPs, and public sector leadership
*Link: [./tracks/govt_registry_20260614/](./tracks/govt_registry_20260614/)*
- *Phase 1–2: Registry schema, compilation pipeline, multi-remote git redundancy* ✅
- *Phase 3: Directory expansion to all 600+ agencies (deferred)*
- *Phase 4: Political parties, MPs, and public sector leadership accounts (new)*
- *Phase 5: Crawling, stealth & academic/decentralized archiving (deferred)*

## [x] Track: Implement mirror account follow synchronization using supported platform APIs and manual review.
*Link: [./tracks/sync_mirror_follows_20260614/](./tracks/sync_mirror_follows_20260614/)*

LinkedIn is source-only and archive-only for now. Deferred outbound platform
mirrors must be created as separate conductor tracks after the Courts of New
Zealand archive and corpus pipeline is stable, with no posting under Dylan
Mordaunt, `edithatogo`, or other personal identities.
