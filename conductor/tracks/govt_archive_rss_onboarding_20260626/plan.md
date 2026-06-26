# Plan - NZ Government Archive - multi-agency RSS feed onboarding and capture

## Track Metadata
- **Track ID**: `govt_archive_rss_onboarding_20260626`
- **Title**: NZ Government Archive - multi-agency RSS feed onboarding and capture
- **Description**: Capture and archive RSS/Atom feeds from all discovered government agencies with active feeds.
- **Date Created**: 2026-06-26
- **Status**: Pending

## Dependencies
- **Depends on**: `govt_archive_per_agency_configs_20260626` (per-agency configs must exist)
- Depends on `govt_archive_readiness_matrix_20260625` (completed)
- Depends on `govt_archive_noncredential_adapters_20260625` (completed)
- **Is dependency gate for**: `govt_archive_scheduled_multisource_20260626`

## Implementation Rules for Less-Capable Agents
- Work phases in order; do not skip dependency gates.
- After each phase, run `$conductor-review`, apply findings, rerun focused tests, then commit.
- Add a git note to every phase commit summarizing scope, tests, residual blockers, and next action.
- Use `feedparser` for RSS/Atom parsing as evaluated in non-credential adapters track.
- Respect rate limits and use `httpx` with retry/backoff for feed fetching.

## Phase 1: Identify all RSS feed URLs per agency
- [ ] Task 1: Compile the full list of RSS feed URLs from the readiness matrix across all agencies.
- [ ] Task 2: Confirm 70 RSS sources identified across all government agencies.
- [ ] Task 3: Map feeds to agencies using agency configs from `govt_archive_per_agency_configs_20260626`.
- [ ] Task 4: Verify 12 agencies with captured content have correct feed URLs assigned.
- [ ] Task 5: Document any feed URLs that failed resolution or returned errors.

## Phase 2: Create per-agency RSS feed configs
- [ ] Task 6: Generate per-agency RSS feed configuration files referencing discovered feed URLs.
- [ ] Task 7: Include feed metadata (feed type, update frequency, content type, last-modified headers).
- [ ] Task 8: Store configs alongside agency source configs in `configs/rss/` directory.
- [ ] Task 9: Validate feed configs against live feed endpoints (HTTP 200, valid XML/JSON).

## Phase 3: Run RSS capture for all agencies
- [ ] Task 10: Execute RSS capture workflow for all configured agency feeds.
- [ ] Task 11: Confirm 421 entries captured across all agencies.
- [ ] Task 12: Verify captured entries include title, published date, URL, and content/summary.
- [ ] Task 13: Check for duplicate entries across capture runs and apply deduplication.
- [ ] Task 14: Validate captured data against original feed content for sampling of feeds.
- [ ] Task 15: Generate capture summary report with per-agency entry counts.

## Phase 4: Set up ongoing scheduled RSS capture
- [ ] Task 16: Create GitHub Actions workflow for scheduled daily RSS capture (`archive_rss_scheduled.yml`).
- [ ] Task 17: Configure workflow to use per-agency RSS configs and emit capture manifests.
- [ ] Task 18: Add workflow_dispatch trigger for manual re-capture of specific agencies.
- [ ] Task 19: Verify scheduled workflow runs successfully in dry-run mode.

## Acceptance Criteria
- [ ] All 70 discovered RSS feeds are configured and captured.
- [ ] 421+ RSS entries archived with full metadata.
- [ ] Per-agency capture manifests available for downstream publication.
- [ ] Scheduled daily capture workflow is active and verified.

## Commit and Review Protocol
- Commit after each phase with a concise hyphenated message.
- Add `git notes` describing implementation evidence and review status.
- Run `$conductor-review` after each phase and auto-apply review fixes before starting the next phase.
