# Plan - NZ Government Archive - explicit credentialed platform onboarding backlog

## Dependencies
Depends on `govt_archive_quality_observability_20260625`.

## Phase 1: Boundaries
- [x] Task 1: Define archive-only, mirror-capable, manual-only, API-capable, and prohibited states for each platform.
- [x] Task 2: Keep LinkedIn, Facebook, Instagram, Threads, and X non-live unless account/API access is validated.
- [x] Task 3: Keep personal identities out of posting and account creation.

## Phase 2: Manual Seed Backlog
- [x] Task 4: Record public profile URLs and evidence pages before API capture is available.
- [x] Task 5: Store onboarding checklists for app registration, token scopes, page/account IDs, and verification probes.
- [x] Task 6: Use `blocked_credential` readiness states rather than capture failures.

## Phase 3: Future Automation
- [x] Task 7: Prefer official APIs, export tools, public RSS/OEmbed endpoints, or sanctioned data access.
- [x] Task 8: Allow browser-assisted setup only for user-driven administration, not unattended GitHub capture.
- [x] Task 9: Design each platform as a separate adapter and workflow with dry-run/live gates.

## Phase 4: Review and Handoff
- [x] Task 10: Run `$conductor-review` after each platform checklist.
- [x] Task 11: Add git notes with exact user actions required before implementation can proceed.

