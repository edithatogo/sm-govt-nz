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
- No credentials or tokens required for RSS-feed-based YouTube metadata capture.

## Phase 1: Identify YouTube channels per agency
- [ ] Task 1: Compile the full list of NZ government YouTube channel URLs/IDs from the registry and readiness matrix.
- [ ] Task 2: Confirm 175 channels discovered across all government agencies.
- [ ] Task 3: Map each channel to its parent agency using registry data.
- [ ] Task 4: Verify each channel is accessible (valid channel URL, public videos exist).
- [ ] Task 5: Document channel metadata (channel name, subscriber count, video count, creation date).

## Phase 2: Create YouTube source contracts per agency
- [ ] Task 6: Generate per-agency YouTube source config files specifying channel IDs and capture parameters.
- [ ] Task 7: Include channel RSS feed URL (e.g., `https://www.youtube.com/feeds/videos.xml?channel_id=...`) and Data API fallback.
- [ ] Task 8: Store configs in `config/youtube/` directory referenced by agency ID.
- [ ] Task 9: Validate channel RSS feeds resolve and return valid video entries.

## Phase 3: Run initial YouTube metadata capture via GitHub Actions
- [ ] Task 10: Trigger `archive_registered_sources.yml` via `workflow_dispatch` with `--source-type youtube --dry-run true` and confirm 175 channels selected.
- [ ] Task 11: Run YouTube metadata capture via `archive_registered_sources.yml` with `--source-type youtube --dry-run false` for all channels.
- [ ] Task 12: For each channel, capture video title, description, published date, video URL, duration, and thumbnail URL.
- [ ] Task 13: Store captured metadata in agency archive directories under `historical_archive_normalized/youtube/` in normalized JSON format.
- [ ] Task 14: Handle rate limits (via RSS feeds where possible to avoid Data API quota usage).
- [ ] Task 15: Generate capture manifest with per-channel video counts and capture timestamps.

## Phase 4: Set up ongoing YouTube archival via GitHub Actions
- [ ] Task 16: Create `.github/workflows/archive_youtube_scheduled.yml` for scheduled weekly YouTube metadata capture (e.g., `cron: "17 2 * * 0"`).
- [ ] Task 17: Configure workflow to only pull new/updated videos since last capture (incremental, using RSS feed pubDate tracking).
- [ ] Task 18: Add `workflow_dispatch` trigger with parameters: `agency_id`, `dry_run`, `channel_limit`.
- [ ] Task 19: Verify workflow runs successfully via `workflow_dispatch` before enabling cron schedule.
- [ ] Task 20: Enable cron schedule and confirm first auto-run completes.

## Acceptance Criteria
- [ ] All 175 YouTube channels are configured and capturing metadata via GitHub Actions.
- [ ] Video metadata archived per channel with consistent schema.
- [ ] Per-channel capture manifests available for downstream publication.
- [ ] `archive_youtube_scheduled.yml` workflow is active and verified with at least one successful auto-run.

## Commit and Review Protocol
- Commit after each phase with a concise hyphenated message.
- Add `git notes` describing implementation evidence and review status.
- Run `$conductor-review` after each phase and auto-apply review fixes before starting the next phase.
