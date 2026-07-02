# Plan - NZ Government Archive - gap prioritization and seed intake hardening

## Phase 1: Gap Priority Model

- [x] Task 1: Define archive gap priority classes for existing-resource fixes, seed-input gaps, operator/API access needs, and larger browser/access projects. Completed in `87d9842`.
- [x] Task 2: Extend failure triage items with priority and priority description fields. Completed in `87d9842`.
- [x] Task 3: Add a deterministic gap-map generator that aggregates archive reports into priority and status counts. Completed in `87d9842`.

## Phase 2: Workflow Integration

- [x] Task 4: Generate and commit `conductor/archive_gap_map.json` from non-dry-run registered-source captures. Completed in `87d9842`.
- [x] Task 5: Generate and commit dedicated website and YouTube gap-map artifacts from scheduled capture workflows. Completed in `87d9842`.
- [x] Task 6: Preserve monthly publication guard behavior and avoid duplicate external releases. Completed in `87d9842`.

## Phase 3: Seed Intake and Existing-Resource Fixes

- [x] Task 7: Add manual seed intake documentation for Threads, LinkedIn, newsletter/email, X, YouTube, Facebook, and Instagram seed directories. Completed in `87d9842`.
- [x] Task 8: Add tracked LinkedIn and newsletter seed templates despite `manual_archive_seeds/` being ignored by default. Completed in `87d9842`.
- [x] Task 9: Normalize obvious malformed YouTube `@handle` URLs with accidental spaces before fetch. Completed in `87d9842`.

## Phase 4: Tests and Handoff

- [x] Task 10: Add tests for gap-map priority classification. Completed in `87d9842`.
- [x] Task 11: Add tests for workflow gap-map hooks. Completed in `87d9842`.
- [x] Task 12: Add tests for YouTube handle-space normalization. Completed in `87d9842`.
- [x] Task 13: Document residual gaps as seed-input, platform-access, or larger browser/access work rather than treating them as workflow failures. Completed in `87d9842`.
- [x] Task 14: Remove Python 3.14 invalid escape warning from visible X browser card extraction. Completed in follow-up track commit.
