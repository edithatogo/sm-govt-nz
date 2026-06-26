# Plan - NZ Government Archive - multi-agency YouTube channel archival

## Track Metadata
- **Track ID**: `govt_archive_youtube_onboarding_20260626`
- **Title**: NZ Government Archive - multi-agency YouTube channel archival
- **Description**: Archive video metadata from all discovered NZ government YouTube channels.
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
- Prefer YouTube channel RSS feeds for routine metadata capture; use the Data API only for resolver gaps.
- Do not download video files; archive only metadata (title, description, published date, duration, thumbnails).

## Phase 1: Identify YouTube channels per agency
- [ ] Task 1: Compile the full list of NZ government YouTube channel URLs/IDs from the registry and readiness matrix.
- [ ] Task 2: Confirm 175 channels discovered across all government agencies.
- [ ] Task 3: Map each channel to its parent agency using registry data.
- [ ] Task 4: Verify each channel is accessible (valid channel URL, public videos exist).
- [ ] Task 5: Document channel metadata (channel name, subscriber count, video count, creation date).

## Phase 2: Create YouTube source contracts per agency
- [ ] Task 6: Generate per-agency YouTube source config files specifying channel IDs and capture parameters.
- [ ] Task 7: Include channel RSS feed URL (e.g., `https://www.youtube.com/feeds/videos.xml?channel_id=...`) and Data API fallback.
- [ ] Task 8: Store configs in `configs/youtube/` directory referenced by agency ID.
- [ ] Task 9: Validate channel RSS feeds resolve and return valid video entries.

## Phase 3: Run initial YouTube metadata capture
- [ ] Task 10: Execute YouTube metadata capture for all 175 channels across all agencies.
- [ ] Task 11: For each channel, capture video title, description, published date, video URL, duration, and thumbnail URL.
- [ ] Task 12: Store captured metadata in agency archive directories in normalized JSON format.
- [ ] Task 13: Handle rate limits (via RSS feeds where possible, Data API with appropriate quotas).
- [ ] Task 14: Generate capture manifest with per-channel video counts and capture timestamps.

## Phase 4: Set up ongoing YouTube archival
- [ ] Task 15: Create GitHub Actions workflow for scheduled weekly YouTube metadata capture (`archive_youtube_scheduled.yml`).
- [ ] Task 16: Configure workflow to only pull new/updated videos since last capture (incremental).
- [ ] Task 17: Add workflow_dispatch trigger for manual re-capture of specific channels.
- [ ] Task 18: Verify scheduled workflow runs successfully in dry-run mode.

## Acceptance Criteria
- [ ] All 175 YouTube channels are configured and capturing metadata.
- [ ] Video metadata archived per channel with consistent schema.
- [ ] Per-channel capture manifests available for downstream publication.
- [ ] Scheduled weekly YouTube capture workflow is active and verified.

## Commit and Review Protocol
- Commit after each phase with a concise hyphenated message.
- Add `git notes` describing implementation evidence and review status.
- Run `$conductor-review` after each phase and auto-apply review fixes before starting the next phase.
