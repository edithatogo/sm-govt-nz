# Plan - NZ Government Archive - maximise non-credential source capture

## Dependencies
Depends on `govt_archive_readiness_matrix_20260625`.

## Implementation Rules for Less-Capable Agents
- Implement one adapter family at a time.
- Do not touch credentialed outbound mirroring while completing this track.
- After each phase, run `$conductor-review`, apply fixes, rerun focused tests, commit, and add a git note.

## Phase 1: Adapter Ranking
- [ ] Task 1: Rank website_page, rss, youtube, bluesky, newsletter_page, sitemap, and media_release sources by archival value and feasibility.
- [ ] Task 2: Mark Meta, LinkedIn, and X as credential/manual/API-onboarding unless a supported public archive endpoint exists.
- [ ] Task 3: Add a source-type risk field for legal, technical, credential, and rate-limit constraints.

## Phase 2: Library and Parser Evaluation
- [ ] Task 4: Evaluate `feedparser` for RSS/Atom date, GUID, and enclosure handling.
- [ ] Task 5: Evaluate `httpx` with retry/backoff, redirect logging, timeout policy, and explicit user-agent settings.
- [ ] Task 6: Evaluate `trafilatura` or equivalent extraction while preserving raw HTML.
- [ ] Task 7: Prefer YouTube channel RSS for routine capture; use heavier tools only for resolver gaps.

## Phase 3: Workflows
- [ ] Task 8: Add per-source-type workflow_dispatch inputs for dry-run/live captures.
- [ ] Task 9: Ensure live runs emit source health, normalized shard manifests, and publication status.
- [ ] Task 10: Keep raw/normalized payload commits opt-in and default to external artifacts.

## Phase 4: Review and Handoff
- [ ] Task 11: Run `$conductor-review` after each adapter family.
- [ ] Task 12: Auto-apply review fixes and rerun focused tests.
- [ ] Task 13: Add git notes with source counts and blocked classes.
