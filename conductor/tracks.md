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

## [x] Track: Archive Courts of New Zealand multi-source records and publish datasets
*Link: [./tracks/courts_nz_multisource_archive_20260612/](./tracks/courts_nz_multisource_archive_20260612/)*
- All implementation phases complete: 43 of 47 plan tasks done, 4 explicitly
  paused/deferred per user decision (LinkedIn capture, Phases 3/4; permanent
  Cloudflare email routing address pending domain registration; 2 standing
  governance items for future platform accounts). Multi-Source Blocker Status
  check reports `complete: true`. Hugging Face dataset
  (`courts-nz-public-notices-archive`) and Zenodo v1 DOI
  (`10.5281/zenodo.20690547`) are live.

## [x] Track: Establish Courts of New Zealand Bluesky mirror account
*Link: [./tracks/courts_nz_bluesky_mirror_20260612/](./tracks/courts_nz_bluesky_mirror_20260612/)*

## [x] Track: Establish Courts of New Zealand Threads mirror account
*Link: [./tracks/courts_nz_threads_mirror_20260612/](./tracks/courts_nz_threads_mirror_20260612/)*

## [x] Track: Complete Courts of New Zealand Bluesky profile evidence and identity archive
*Link: [./tracks/courts_nz_bluesky_profile_archive_20260613/](./tracks/courts_nz_bluesky_profile_archive_20260613/)*

## [x] Track: Complete Courts of New Zealand Bluesky archive replay and manifest telemetry
*Link: [./tracks/courts_nz_bluesky_archive_replay_20260613/](./tracks/courts_nz_bluesky_archive_replay_20260613/)*
- 50/50 Bluesky-source records and 689/689 recovered X records are reflected in
  Bluesky mirror coverage. Replay infrastructure, duplicate safety, delivery
  verification, and exclusion telemetry are complete; unreplayable exclusions
  are 0. Manual `Archive Replay` remains bounded to reviewed batches of 5, 10,
  or 20 records for any future replay source.

## [x] Track: Harden Courts of New Zealand Bluesky mirror launch operations
*Link: [./tracks/courts_nz_bluesky_launch_ops_20260613/](./tracks/courts_nz_bluesky_launch_ops_20260613/)*

## [x] Track: Implement Courts of New Zealand Threads API credentials and validation
*Link: [./tracks/courts_nz_threads_api_credentials_20260613/](./tracks/courts_nz_threads_api_credentials_20260613/)*

## [x] Track: Implement Courts of New Zealand Threads adapter and controlled launch
*Link: [./tracks/courts_nz_threads_adapter_launch_20260613/](./tracks/courts_nz_threads_adapter_launch_20260613/)*

## [x] Track: Decide Courts of New Zealand Threads historical replay policy
*Link: [./tracks/courts_nz_threads_historical_replay_policy_20260613/](./tracks/courts_nz_threads_historical_replay_policy_20260613/)*

## [x] Track: Implement Courts of New Zealand Instagram mirror via Meta APIs
*Link: [./tracks/courts_nz_instagram_meta_api_20260613/](./tracks/courts_nz_instagram_meta_api_20260613/)*
- All 15 implementation tasks complete. Track resolved as **intentionally deferred**
  in `courts_nz_instagram_launch_reconciliation_20260617`. Launch remains gated on
  `INSTAGRAM_ACCESS_TOKEN`/`INSTAGRAM_USER_ID` secrets and API verification of
  `@mirnzcourts`; runtime keeps `instagram.enabled` false until both are available.

## [x] Track: Reconcile Courts of New Zealand Instagram launch runtime state
*Link: [./tracks/courts_nz_instagram_launch_reconciliation_20260617/](./tracks/courts_nz_instagram_launch_reconciliation_20260617/)*
- Outcome: deferred; missing `INSTAGRAM_ACCESS_TOKEN` and `INSTAGRAM_USER_ID`.

## [x] Track: Select and launch Courts of New Zealand X/Twitter mirror route
*Link: [./tracks/courts_nz_x_twitter_launch_route_20260617/](./tracks/courts_nz_x_twitter_launch_route_20260617/)*
- Buffer route live: current-head validation, controlled live send, delivery state
  commit, and first scheduled run all complete (runs `27724263224`, `27724295494`,
  `27724325327`, `27724489515`). Public X URL verification is documented as a
  known Buffer API limitation (Buffer returns `sent` status without exposing the
  final `/MirNZCourts/status/...` provider URL); this is operationally tracked but
  not a blocker for the launch itself.

## [x] Track: Implement Courts of New Zealand Facebook Page mirror via Meta APIs
*Link: [./tracks/courts_nz_facebook_meta_api_20260613/](./tracks/courts_nz_facebook_meta_api_20260613/)*
- Deferred. Adapter, probe, validation, secrets schema, dry-run, and tests
  complete. Blocked on Facebook Page creation by a Meta admin and
  `FACEBOOK_PAGE_ACCESS_TOKEN`/`FACEBOOK_PAGE_ID` secrets setup.

## [x] Track: Define Courts of New Zealand archive publication cadence
*Link: [./tracks/courts_nz_archive_publication_cadence_20260617/](./tracks/courts_nz_archive_publication_cadence_20260617/)*
- Hugging Face: weekly rolling update via scheduled Publish Archives (target: huggingface)
- Zenodo: manual release snapshot lane, requires publish-zenodo-doi confirmation
- Machine-readable contract: config/courts_nz_archive_publication_cadence.json

## [x] Track: NZ Government Social Media Registry — agencies, political parties, MPs, and public sector leadership
*Link: [./tracks/govt_registry_20260614/](./tracks/govt_registry_20260614/)*
- Phase 1–2: Registry schema, compilation pipeline, multi-remote git redundancy ✅
- Phase 3: Twitter/X deactivation archive & registry seeding (252 agencies, 483 profiles) ✅
- Phase 4: Syndication & mirroring implementation (unified feed dry-run passed, gated) ✅
- Phase 5: Political parties, MPs, leadership — schema, validation, reference integrity CI gate ✅
  - Reference integrity gap report is complete: 0 missing party leaders,
    0 missing party presidents, 0 unknown party references, and 0 unknown role
    organization references.
  - Deferred: manual research of remaining parties/MPs/leaders, syndication
    classification, tenure-linked profiles
- Spec Phases 3/5: Directory expansion to 600+ agencies, crawling & archival automation (deferred)

## [x] Track: Implement mirror account follow synchronization using supported platform APIs and manual review.
*Link: [./tracks/sync_mirror_follows_20260614/](./tracks/sync_mirror_follows_20260614/)*

LinkedIn is source-only and archive-only for now. Deferred outbound platform
mirrors must be created as separate conductor tracks after the Courts of New
Zealand archive and corpus pipeline is stable, with no posting under Dylan
Mordaunt, `edithatogo`, or other personal identities.

## [x] Track: NZ Government Social Media Registry — full expansion: MPs, parties, public sector leaders, historical figures
*Link: [./tracks/govt_registry_mp_expansion_20260621/](./tracks/govt_registry_mp_expansion_20260621/)*
- Phase 0 complete (tooling + track setup)
- Phase 1 batch 1/3 complete (16 National Cabinet/ministers added → 73 total persons)
- Continuing with remaining National MPs, then Labour, Green, ACT, NZ First, Te Pāti Māori,
  historical figures (working backwards), public sector leaders, syndication classification,
  and tenure-linked profiles.
