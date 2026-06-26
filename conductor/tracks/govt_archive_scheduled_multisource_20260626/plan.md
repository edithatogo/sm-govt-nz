# Plan - NZ Government Archive - scheduled multi-agency capture workflow

## Track Metadata
- **Track ID**: `govt_archive_scheduled_multisource_20260626`
- **Title**: NZ Government Archive - scheduled multi-agency capture workflow
- **Description**: Set up GitHub Actions scheduled workflows for multi-agency archival capture across all source types.
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
- All per-source-type capture scripts must be finalized before scheduling.
- Use cron schedule expressions that respect agency server loads and API rate limits.

## Phase 1: Update archive_registered_sources.yml with scheduled trigger
- [ ] Task 1: Add `schedule` trigger block to `.github/workflows/archive_registered_sources.yml`.
- [ ] Task 2: Configure cron schedule (e.g., daily at 02:00 UTC) for the master workflow.
- [ ] Task 3: Ensure workflow reads per-agency configs from `configs/agencies/` directory.
- [ ] Task 4: Add notification/alerting on workflow failure (GitHub issue or commit check).
- [ ] Task 5: Test workflow with `workflow_dispatch` before enabling schedule.

## Phase 2: Create per-source-type scheduled workflows
- [ ] Task 6: Create `archive_rss_scheduled.yml` — scheduled daily RSS capture across all agencies.
- [ ] Task 7: Create `archive_bluesky_scheduled.yml` — scheduled every-6-hour Bluesky capture.
- [ ] Task 8: Create `archive_website_scheduled.yml` — scheduled weekly website page capture.
- [ ] Task 9: Create `archive_youtube_scheduled.yml` — scheduled weekly YouTube metadata capture.
- [ ] Task 10: Each workflow should support `workflow_dispatch` with agency and dry-run parameters.
- [ ] Task 11: Ensure workflows emit structured capture manifests and health telemetry.

## Phase 3: Set up multi-agency archive state tracking
- [ ] Task 12: Create archive state tracking file (`conductor/archive_state.json`) tracking last-capture timestamps per agency per source type.
- [ ] Task 13: Update state file after each scheduled capture run with capture results.
- [ ] Task 14: Add staleness detection alerting for agencies/sources missed beyond configured TTL.
- [ ] Task 15: Ensure state file is committed to repo for traceability (or published as artifact).

## Phase 4: Verify scheduled runs
- [ ] Task 16: Trigger each per-source-type workflow via `workflow_dispatch` and verify successful execution.
- [ ] Task 17: Verify the master `archive_registered_sources.yml` runs end-to-end with all source types.
- [ ] Task 18: Check archive state is updated correctly after each run.
- [ ] Task 19: Enable cron schedule triggers and confirm first auto-run completes.
- [ ] Task 20: Document schedule summary in `conductor/schedule_documentation.md`.

## Acceptance Criteria
- [ ] Master scheduled workflow runs automatically on cron schedule.
- [ ] Per-source-type scheduled workflows run at appropriate cadences (RSS daily, Bluesky every 6h, website weekly, YouTube weekly).
- [ ] Multi-agency archive state tracking is active and captures are recorded.
- [ ] All workflows verified with at least one successful run.
- [ ] Schedule documentation available in conductor directory.

## Commit and Review Protocol
- Commit after each phase with a concise hyphenated message.
- Add `git notes` describing implementation evidence and review status.
- Run `$conductor-review` after each phase and auto-apply review fixes before starting the next phase.
