# Plan - Courts of New Zealand Instagram Meta API Mirror

## Phase 1: Account and API Readiness
- [x] Task: Record that the Instagram mirror account has been created and keep
  posting disabled until API validation completes.
- [ ] Task: Confirm Instagram account type, profile ID, and Meta app
  permissions required for publishing.
- [x] Task: Confirm whether the Threads Meta account/admin can own the
  Instagram mirror without using a personal posting identity.
- [ ] Task: Document token lifetime, refresh, and app-review requirements.

## Phase 2: Secret and Probe Contract
- [x] Task: Add Instagram secret names to `config/secrets.schema.json`.
- [x] Task: Extend secret validation for `--target instagram`.
- [x] Task: Add a non-posting Instagram profile probe.
- [x] Task: Add a manual GitHub validation workflow or extend Meta validation
  without enabling posting.

## Phase 3: Adapter and State
- [ ] Task: Implement an Instagram adapter behind `instagram.enabled`.
- [ ] Task: Add separate duplicate-prevention state.
- [ ] Task: Add tests for media payloads, attribution, errors, and disabled
  default behavior.

## Phase 4: Controlled Launch
- [ ] Task: Run a dry-run mapping for the latest Courts source post.
- [ ] Task: Review payload and account identity.
- [ ] Task: Run one controlled live post only after approval.
- [ ] Task: Verify public URL and commit state.
