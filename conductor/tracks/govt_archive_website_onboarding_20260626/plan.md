# Plan - NZ Government Archive - multi-agency website page archiving

## Track Metadata
- **Track ID**: `govt_archive_website_onboarding_20260626`
- **Title**: NZ Government Archive - multi-agency website page archiving
- **Description**: Archive homepage and key pages for all 200+ government agencies.
- **Date Created**: 2026-06-26
- **Status**: Complete

## Dependencies
- **Depends on**: `govt_archive_per_agency_configs_20260626` (per-agency configs must exist)
- Depends on `govt_archive_readiness_matrix_20260625` (completed)
- Depends on `govt_archive_noncredential_adapters_20260625` (completed)
- **Is dependency gate for**: `govt_archive_scheduled_multisource_20260626`

## Implementation Rules for Less-Capable Agents
- Work phases in order; do not skip dependency gates.
- After each phase, run `$conductor-review`, apply findings, rerun focused tests, then commit.
- Add a git note to every phase commit summarizing scope, tests, residual blockers, and next action.
- Use `httpx` with retry/backoff for page fetching; prefer raw HTML storage with `trafilatura` for text extraction.
- Respect robots.txt and set polite crawl delays.
- No credentials or tokens required -- all NZ government websites are public.

## Phase 1: Identify seed pages per agency
- [x] Task 1: Compile the full list of agency homepage URLs from the registry and readiness matrix.
- [x] Task 2: Confirm 247 homepages are listed in the manifest.
- [x] Task 3: Validate each URL is reachable (HTTP 200) and resolves correctly.
- [x] Task 4: Identify additional seed pages beyond homepages (e.g., About, Contact, News, Publications) per agency.
- [x] Task 5: Document any URLs that are redirecting, broken, or returning errors.

## Phase 2: Create agency website page contracts
- [x] Task 6: Define per-agency website page contracts specifying which pages to archive.
- [x] Task 7: Include crawl depth, page types (homepage, about, news, publications, contact), and update frequency.
- [x] Task 8: Store contracts in `config/website/` directory referenced by agency ID.
- [x] Task 9: Validate contracts against live sites to confirm page structure and URL patterns.

## Phase 3: Run initial website page capture via GitHub Actions
- [x] Task 10: Trigger `archive_registered_sources.yml` via `workflow_dispatch` with `--source-type website_page --dry-run true` and confirm 247 homepages selected.
- [x] Task 11: Run initial website capture via `archive_registered_sources.yml` with `--source-type website_page --dry-run false` for all 247 homepages.
- [x] Task 12: Verify raw HTML is captured and stored with HTTP response headers (status, content-type, last-modified).
- [x] Task 13: Run text extraction via `trafilatura` on captured HTML for normalized content.
- [x] Task 14: Store raw HTML and extracted text in agency archive directories under `historical_archive_raw/website/` and `historical_archive_normalized/website/`.
- [x] Task 15: Generate capture manifest with per-agency page counts and capture timestamps.
- [x] Task 16: Handle capture failures gracefully with retry logic and error logging.

## Phase 4: Set up ongoing website page archival via GitHub Actions
- [x] Task 17: Create `.github/workflows/archive_website_scheduled.yml` for scheduled weekly website capture (e.g., `cron: "7 2 * * 0"`).
- [x] Task 18: Configure workflow to respect crawl delays (3-second delay between requests) and avoid overwhelming agency servers.
- [x] Task 19: Add incremental capture support (only re-capture pages older than configured TTL of 7 days).
- [x] Task 20: Add `workflow_dispatch` trigger with parameters: `agency_id`, `dry_run`, `page_limit`.
- [x] Task 21: Verify workflow runs successfully via `workflow_dispatch` before enabling cron schedule.
- [x] Task 22: Enable cron schedule and confirm first auto-run completes.

## Acceptance Criteria
- [x] All 247 agency homepages captured with raw HTML and extracted text via GitHub Actions.
- [x] Per-agency website page contracts defined and validated.
- [x] Website capture manifest generated with per-agency counts.
- [x] `archive_website_scheduled.yml` workflow is active and verified with at least one successful auto-run.

## Commit and Review Protocol
- Commit after each phase with a concise hyphenated message.
- Add `git notes` describing implementation evidence and review status.
- Run `$conductor-review` after each phase and auto-apply review fixes before starting the next phase.
