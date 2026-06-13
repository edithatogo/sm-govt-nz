# Plan - Courts of New Zealand Threads Mirror Account

## Phase 1: Account Onboarding
- [x] Task: Create the dedicated Threads mirror account using
  `edithatogo@gmail.com` for administration where practical.
- [x] Task: Configure display name, handle, bio, avatar, banner, and source link
  using the mirror identity contract.
- [x] Task: Archive the source and mirror profile snapshots in the repository.

## Phase 2: API and Secrets
- [x] Task: Confirm the preferred Threads posting route: official Threads API
  first, Buffer second, browser automation deferred.
- [x] Task: Add Threads to the scheduled pipeline as a no-posting readiness gate
  while Bluesky backlog mirroring is still in progress.
- [ ] Task: Add secret schema entries for the selected route.
- [ ] Task: Add a read/write credential validation command that cannot post
  content.

## Phase 3: Posting Adapter
- [ ] Task: Implement a Threads mirror target adapter behind an explicit config
  flag.
- [ ] Task: Add duplicate-prevention state that is separate from archive state.
- [ ] Task: Add tests for attribution, media handling, and no-backlog posting.
- [ ] Task: Add a guardrail test proving historical archive records are not
  replayed to Threads by default.
- [ ] Task: Document Threads historical replay as deferred because it would post
  archival records as current posts rather than preserving original timestamps.

## Phase 4: Controlled Launch
- [ ] Task: Run dry-run mapping for the latest Courts of New Zealand source
  post.
- [ ] Task: Review the generated payload before any live post.
- [ ] Task: Run one controlled live post only after review approval.
- [ ] Task: Verify the live URL and commit updated state.

## Deferred: Historical Replay Review
- [x] Task: Record that Threads historical replay cannot be treated as
  backdated publishing; original timestamps must remain in archive metadata
  and/or mirror text.
- [x] Task: Split remaining Threads work into granular conductor tracks for API
  credentials, adapter launch, and historical replay policy.
- [ ] Task: Estimate API limits, user-facing noise, and attribution impact of a
  Threads historical replay.
- [ ] Task: Proceed only if a separate review approves publishing archived
  records as current Threads posts.
