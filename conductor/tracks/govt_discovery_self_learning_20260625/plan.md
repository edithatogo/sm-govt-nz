# Plan - NZ Government Discovery - self-improving heuristic search and learning loop

## Dependencies
Depends on `govt_archive_readiness_matrix_20260625`.

## Phase 1: Heuristic Corpus
- [ ] Task 1: Track successful and failed discovery hedges for government domains and public-sector entity classes.
- [ ] Task 2: Persist evidence snippets, referring pages, query strings, and candidate scores.
- [ ] Task 3: Classify official, role/office, personal-public, campaign, legacy, duplicate, and spoof-risk accounts.

## Phase 2: Daily Discovery
- [ ] Task 4: Run daily GitHub Actions discovery in bounded dry-run mode.
- [ ] Task 5: Probe homepages, contact pages, footers, sitemaps, RSS auto-discovery, and YouTube links.
- [ ] Task 6: Emit candidate reports with new/already-registered/rejected/needs-review buckets.

## Phase 3: Learning Loop
- [ ] Task 7: Promote high-yield heuristics and demote noisy ones.
- [ ] Task 8: Store false-positive patterns.
- [ ] Task 9: Use deterministic scoring before any LLM summarization.

## Phase 4: Review and Handoff
- [ ] Task 10: Run `$conductor-review` before bulk imports.
- [ ] Task 11: Auto-apply provenance/schema fixes.
- [ ] Task 12: Add git notes with heuristic changes and candidate-count deltas.
