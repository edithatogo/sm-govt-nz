# Plan - Courts of New Zealand Facebook Page Meta API Mirror

## Phase 1: Page and API Readiness
- [ ] Task: Create or confirm the dedicated Facebook Page mirror identity.
- [ ] Task: Confirm Page ID, page access token, app permissions, and app-review
  requirements for publishing.
- [ ] Task: Confirm the same Meta account/admin can manage the Page without
  using a personal posting identity.

## Phase 2: Secret and Probe Contract
- [ ] Task: Add Facebook Page secret names to `config/secrets.schema.json`.
- [ ] Task: Extend secret validation for `--target facebook`.
- [ ] Task: Add a non-posting Facebook Page identity/permission probe.
- [ ] Task: Add a manual GitHub validation workflow or extend Meta validation
  without enabling posting.

## Phase 3: Adapter and State
- [ ] Task: Implement a Facebook Page adapter behind `facebook.enabled`.
- [ ] Task: Add separate duplicate-prevention state.
- [ ] Task: Add tests for page post payloads, attribution, errors, and disabled
  default behavior.

## Phase 4: Controlled Launch
- [ ] Task: Run a dry-run mapping for the latest Courts source post.
- [ ] Task: Review payload and Page identity.
- [ ] Task: Run one controlled live post only after approval.
- [ ] Task: Verify public URL and commit state.
