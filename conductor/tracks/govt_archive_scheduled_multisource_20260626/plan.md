# Plan - NZ Government Archive - scheduled multi-agency capture workflow

## Track Metadata
- **Track ID**: `govt_archive_scheduled_multisource_20260626`
- **Title**: NZ Government Archive - scheduled multi-agency capture workflow
- **Description**: Set up GitHub Actions scheduled workflows for multi-agency archival capture across all non-credentialed source types (RSS, Bluesky, website, YouTube).
- **Date Created**: 2026-06-26
- **Status**: Pending

## Dependencies
- **Depends on**: `govt_archive_per_agency_configs_20260626` (configs must exist)
- **Depends on**: `govt_archive_rss_onboarding_20260626` (RSS capture working)
- **Depends on**: `govt_archive_bluesky_onboarding_20260626` (Bluesky capture working)
- **Depends on**: `govt_archive_website_onboarding_20260626` (Website capture working)
- **Depends on**: `govt_archive_youtube_onboarding_20260626` (YouTube capture working)
- Depends on `govt_archive_readiness_matrix_20260625` (completed)
- Depends on `govt_archive_quality_observability_20260625` (completed)

## Implementation Rules for Less-Capable Agents
- Work phases in order; do not skip dependency gates.
- After each phase, run `$conductor-review`, apply findings, rerun focused tests, then commit.
- Add a git note to every phase commit summarizing scope, tests, residual blockers, and next action.
- All per-source-type capture scripts must be finalized and working on GitHub Actions before scheduling.
- Use cron schedule expressions that respect agency server loads and API rate limits.
- No credentials or tokens required -- all four source types (RSS, Bluesky public API, website HTML, YouTube RSS) are publicly accessible.

## Phase 1: Add schedule trigger to archive_registered_sources.yml master workflow
- [ ] Task 1: Add `schedule` trigger block to `.github/workflows/archive_registered_sources.yml` with daily cron (e.g., `cron: "0 2 * * *"`).
- [ ] Task 2: Configure workflow to run `python -m scripts.archive_registered_sources --source-type all_feasible --dry-run false` for all non-credentialed source types.
- [ ] Task 3: Ensure workflow reads per-agency configs from `config/` directory.
- [ ] Task 4: Add `workflow_dispatch` override with per-source-type selection.
- [ ] Task 5: Add notification/alerting on workflow failure via GitHub commit check annotation.
- [ ] Task 6: Test master workflow with `workflow_dispatch --source-type all_feasible --dry-run true` to confirm source selection.

## Phase 2: Create per-source-type scheduled workflows (or verify existing ones)
- [ ] Task 7: Verify `archive_rss_scheduled.yml` exists from Track 2 and has correct daily schedule.
- [ ] Task 8: Verify `archive_bluesky_scheduled.yml` exists from Track 3 and has correct every-6-hour schedule.
- [ ] Task 9: Verify `archive_website_scheduled.yml` exists from Track 4 and has correct weekly schedule.
- [ ] Task 10: Verify `archive_youtube_scheduled.yml` exists from Track 5 and has correct weekly schedule.
- [ ] Task 11: Each workflow should support `workflow_dispatch` with agency_id and dry_run parameters.
- [ ] Task 12: Ensure all workflows emit structured capture manifests and health telemetry to `conductor/archive_source_health.json`.

## Phase 3: Set up multi-agency archive state tracking
- [ ] Task 13: Verify `conductor/archive_state.json` tracks last-capture timestamps per agency per source type.
- [ ] Task 14: Update state file after each scheduled capture run with capture results (entry counts, success/failure status).
- [ ] Task 15: Add staleness detection -- flag agencies/sources not captured beyond configured TTL (RSS: 24h, Bluesky: 6h, Website: 7d, YouTube: 7d).
- [ ] Task 16: Ensure state file is committed to repo for traceability (lightweight, manifest-only, not raw payloads).

## Phase 4: Create archive health report and staleness alerting
- [ ] Task 17: Create `scripts/check_archive_staleness.py` that reads `archive_state.json` and warns about sources not captured within TTL.
- [ ] Task 18: Create `.github/workflows/archive_health_monitor.yml` scheduled weekly health check that runs the staleness checker.
- [ ] Task 19: Configure health monitor to create a GitHub Issue if any source type has stale captures.
- [ ] Task 20: Verify health monitor via `workflow_dispatch`.

## Phase 5: Verify all scheduled runs end-to-end
- [ ] Task 21: Trigger each per-source-type workflow via `workflow_dispatch` and verify successful execution.
- [ ] Task 22: Verify the master `archive_registered_sources.yml` runs end-to-end with all source types.
- [ ] Task 23: Check `conductor/archive_state.json` is updated correctly after each run.
- [ ] Task 24: Enable cron schedule triggers on all workflows and confirm first auto-run completes.
- [ ] Task 25: Verify archive health monitor produces clean report (no stale sources).
- [ ] Task 26: Document schedule summary in `conductor/schedule_documentation.md`.

## Acceptance Criteria
- [ ] Master scheduled workflow (`archive_registered_sources.yml`) runs automatically on daily cron.
- [ ] Per-source-type scheduled workflows run at appropriate cadences (RSS daily, Bluesky every 6h, website weekly, YouTube weekly).
- [ ] Multi-agency archive state tracking is active and captures are recorded in `archive_state.json`.
- [ ] Archive health monitor detects staleness and creates GitHub Issues for stale sources.
- [ ] All workflows verified with at least one successful run.
- [ ] Schedule documentation available in conductor directory.

## Commit and Review Protocol
- Commit after each phase with a concise hyphenated message.
- Add `git notes` describing implementation evidence and review status.
- Run `$conductor-review` after each phase and auto-apply review fixes before starting the next phase.
