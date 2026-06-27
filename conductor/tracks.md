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
- All implementation phases complete: 47 of 47 plan tasks done. LinkedIn
  archive-only seed capture is complete with 2 normalized records; permanent
  Cloudflare email routing remains a zero-spend external guardrail, not an open
  implementation task. Multi-Source Blocker Status check reports `complete: true`. Hugging Face dataset
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

## [x] Track: NZ Government Social Media Registry â€” agencies, political parties, MPs, and public sector leadership
*Link: [./tracks/govt_registry_20260614/](./tracks/govt_registry_20260614/)*
- Phase 1â€“2: Registry schema, compilation pipeline, multi-remote git redundancy âœ…
- Phase 3: Twitter/X deactivation archive & registry seeding (252 agencies, 483 profiles) âœ…
- Phase 4: Syndication & mirroring implementation (unified feed dry-run passed, gated) âœ…
- Phase 5: Political parties, MPs, leadership â€” schema, validation, reference integrity CI gate âœ…
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

## [x] Track: NZ Government Social Media Registry â€” full expansion: MPs, parties, public sector leaders, historical figures
*Link: [./tracks/govt_registry_mp_expansion_20260621/](./tracks/govt_registry_mp_expansion_20260621/)*
- Phase 0 complete (tooling + track setup).
- Current 54th Parliament MP roster coverage is locally complete across National,
  Labour, Greens, ACT, NZ First, and Te Pati Maori: 60 current-MP records added,
  blank social handles reduced to 0, and remaining current MPs without structured
  profile IDs are reviewed in `conductor/current_mp_social_profile_review_20260623.json`.
- Strict registry gates and focused tests pass locally. Phase 7/8 local coverage
  now includes recent former Prime Ministers, former/current Deputy Prime Minister
  continuity, major-party leaders from 1990 onward, Chief Justice Helen Winkelmann,
  and core current public-sector leaders. Persons registry has 190 records. Remote
  push/GitHub Actions verification passed on 2026-06-23.

## [x] Track: NZ Government Social Media Registry â€” provenance and batch quality gates
*Link: [./tracks/govt_registry_quality_gates_20260622/](./tracks/govt_registry_quality_gates_20260622/)*
- Complete: evidence metadata, stricter batch validation, unknown-organization rejection,
  and recomputed reference-integrity checks are in place for further expansion batches.

## [x] Track: NZ Government Social Media Registry â€” verification refresh cadence
*Link: [./tracks/govt_registry_refresh_cadence_20260622/](./tracks/govt_registry_refresh_cadence_20260622/)*
- Tracks monthly and event-triggered re-verification for agencies, parties, MPs,
  public sector leaders, and historical records.
- Complete: optional inline refresh metadata, non-mutating refresh report command,
  and `conductor/registry_refresh_report.json` artifact. Initial 2026-06-22
  queue has 610 due profiles; agencies are the first refresh cohort.

## [x] Track: NZ Government Social Media Registry â€” account classification and tenure-linked profiles
*Link: [./tracks/govt_registry_account_classification_20260622/](./tracks/govt_registry_account_classification_20260622/)*
- Complete: schemas, tests, current seeded-profile classifications, and one
  representative role-linked office profile are in place. Future seeded profiles
  must include `account_classification` and `syndication_classification`.
 
## [x] Track: NZ Government Archive - source readiness matrix and dependency sequencing 
*Link: [./tracks/govt_archive_readiness_matrix_20260625/](./tracks/govt_archive_readiness_matrix_20260625/)* 
- Complete: Readiness matrix with 1637 sources across 11 readiness states and 5 dependency gates. Next track: govt_archive_noncredential_adapters_20260625.
 
## [x] Track: NZ Government Archive - maximise non-credential source capture 
*Link: [./tracks/govt_archive_noncredential_adapters_20260625/](./tracks/govt_archive_noncredential_adapters_20260625/)* 
- Complete: All 13/13 tasks done. Adapter ranking, library evaluation (feedparser, httpx, trafilatura), source-type risk taxonomy, and per-source workflow patterns documented. 
 
## [x] Track: NZ Government Archive - external publication and storage hardening 
*Link: [./tracks/govt_archive_external_publication_20260625/](./tracks/govt_archive_external_publication_20260625/)* 
- Complete: All 11 tasks implemented. Publication targets: Hugging Face, Zenodo, GitHub Artifacts, OSF. Payload commit gating active. 
 
## [x] Track: NZ Government Discovery - self-improving heuristic search and learning loop 
*Link: [./tracks/govt_discovery_self_learning_20260625/](./tracks/govt_discovery_self_learning_20260625/)* 
- Complete: All 13/13 tasks done. Adapter ranking, library evaluation (feedparser, httpx, trafilatura), source-type risk taxonomy, and per-source workflow patterns documented. 
 
## [x] Track: NZ Government Archive - quality gates, observability, and CI/CD resilience 
*Link: [./tracks/govt_archive_quality_observability_20260625/](./tracks/govt_archive_quality_observability_20260625/)* 
- Complete: All 11 tasks implemented. Quality gates, source health observability, CI split quick/scheduled checks. 
 
## [x] Track: NZ Government Archive - explicit credentialed platform onboarding backlog 
*Link: [./tracks/govt_credentialed_platform_onboarding_20260625/](./tracks/govt_credentialed_platform_onboarding_20260625/)* 
- Complete: All 11 tasks implemented. Platform boundaries, manual seed backlog, credential-gated readiness states.
 
## [x] Track: NZ Government Archive - provenance, fixity, and reproducible research packaging 
*Link: [./tracks/govt_archive_provenance_fixity_20260625/](./tracks/govt_archive_provenance_fixity_20260625/)* 
- Planned dependency: govt_archive_external_publication_20260625

## [x] Track: NZ Government Archive - per-agency source inventory and RSS feed configuration
*Link: [./tracks/govt_archive_per_agency_configs_20260626/](./tracks/govt_archive_per_agency_configs_20260626/)*
- Complete: All 18 tasks done. 16 agency configs generated and validated. Agencies index created. GitHub Actions dry-run verified.

## [x] Track: NZ Government Archive - multi-agency RSS feed onboarding and capture
*Link: [./tracks/govt_archive_rss_onboarding_20260626/](./tracks/govt_archive_rss_onboarding_20260626/)*
- Complete: All 21 tasks done. 77 RSS sources configured, 421 entries captured. archive_rss_scheduled.yml active with daily cron.

## [x] Track: NZ Government Archive - multi-agency Bluesky account onboarding and capture
*Link: [./tracks/govt_archive_bluesky_onboarding_20260626/](./tracks/govt_archive_bluesky_onboarding_20260626/)*
- Complete: All 26 tasks done. 4 Bluesky accounts capturing (courtsofnz, beehivenz, healthnz.govt.nz, health.govt.nz). archive_bluesky_scheduled.yml active with every-6h cron.

## [ ] Track: NZ Government Archive - multi-agency website page archiving
*Link: [./tracks/govt_archive_website_onboarding_20260626/](./tracks/govt_archive_website_onboarding_20260626/)*
- 247 homepages in manifest across 200+ agencies. Web archiving pending.

## [ ] Track: NZ Government Archive - multi-agency YouTube channel archival
*Link: [./tracks/govt_archive_youtube_onboarding_20260626/](./tracks/govt_archive_youtube_onboarding_20260626/)*
- 175 YouTube channels discovered. Metadata archival pending.

## [ ] Track: NZ Government Archive - scheduled multi-agency capture workflow
*Link: [./tracks/govt_archive_scheduled_multisource_20260626/](./tracks/govt_archive_scheduled_multisource_20260626/)
- Depends on all per-source-type onboarding tracks completing first.





