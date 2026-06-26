# Plan - NZ Government Archive - multi-agency Bluesky account onboarding and capture

## Track Metadata
- **Track ID**: `govt_archive_bluesky_onboarding_20260626`
- **Title**: NZ Government Archive - multi-agency Bluesky account onboarding and capture
- **Description**: Capture and archive Bluesky posts from all discovered NZ government Bluesky accounts.
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
- Use public Bluesky API endpoints; no credentials required for read-only capture.
- Respect rate limits and pagination (max 100 posts per request).

## Phase 1: Identify all Bluesky accounts
- [ ] Task 1: Compile the full list of NZ government Bluesky account handles from the registry and readiness matrix.
- [ ] Task 2: Confirm 5 accounts: `courtsofnz`, `beehivenz`, `health.govt.nz`, `healthnz.govt.nz`, `independent-childrens-monitor`.
- [ ] Task 3: Verify each account is resolvable via the Bluesky API (valid DID, accessible profile).
- [ ] Task 4: Document account metadata (display name, description, follower count, creation date).

## Phase 2: Create per-agency Bluesky source configurations
- [ ] Task 5: Generate per-agency Bluesky source config files alongside agency configs.
- [ ] Task 6: Include Bluesky DID, handle, profile endpoint URL, and capture parameters.
- [ ] Task 7: Store configs in `configs/bluesky/` directory referenced by agency ID.
- [ ] Task 8: Validate configs against live Bluesky API responses.

## Phase 3: Run Bluesky capture
- [ ] Task 9: Execute Bluesky capture for `courtsofnz` account (DONE - confirmed working).
- [ ] Task 10: Execute Bluesky capture for `beehivenz` account.
- [ ] Task 11: Execute Bluesky capture for `health.govt.nz` account.
- [ ] Task 12: Execute Bluesky capture for `healthnz.govt.nz` account.
- [ ] Task 13: Execute Bluesky capture for `independent-childrens-monitor` account.
- [ ] Task 14: Verify captured posts include full content, timestamp, and metadata.
- [ ] Task 15: Generate per-account capture summary with post counts.

## Phase 4: Archive Bluesky profiles for all accounts
- [ ] Task 16: Capture and store Bluesky profile metadata (avatar, banner, description, links) for each account.
- [ ] Task 17: Generate profile archive snapshot with timestamp for provenance.
- [ ] Task 18: Store profile archives alongside captured posts in agency archive directories.
- [ ] Task 19: Schedule periodic profile refresh (e.g., weekly) to track profile changes.

## Acceptance Criteria
- [ ] All 5 Bluesky accounts are configured and capturing successfully.
- [ ] Bluesky posts archived with full content and metadata for each account.
- [ ] Profile snapshots stored for identity verification and change tracking.
- [ ] Per-account capture manifests available for downstream publication.

## Commit and Review Protocol
- Commit after each phase with a concise hyphenated message.
- Add `git notes` describing implementation evidence and review status.
- Run `$conductor-review` after each phase and auto-apply review fixes before starting the next phase.
