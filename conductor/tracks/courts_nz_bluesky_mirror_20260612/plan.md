# Plan - Courts of New Zealand Bluesky Mirror Account

## Phase 1: Account Onboarding
- [ ] Task: Create the dedicated Bluesky mirror account using
  `edithatogo@gmail.com` for administration where practical.
- [ ] Task: Configure display name, handle, bio, avatar, banner, and source link
  using the mirror identity contract.
- [ ] Task: Archive the source and mirror profile snapshots in the repository.

## Phase 2: API and Secrets
- [ ] Task: Identify the Bluesky posting library/API path and document token
  requirements.
- [ ] Task: Add secret schema entries for the mirror account credentials.
- [ ] Task: Add a read/write credential validation command that cannot post
  content.

## Phase 3: Posting Adapter
- [ ] Task: Implement a Bluesky mirror target adapter behind an explicit config
  flag.
- [ ] Task: Add duplicate-prevention state that is separate from archive state.
- [ ] Task: Add tests for attribution, character limits, and no-backlog posting.

## Phase 4: Controlled Launch
- [ ] Task: Run dry-run mapping for the latest Courts of New Zealand source
  post.
- [ ] Task: Review the generated payload before any live post.
- [ ] Task: Run one controlled live post only after review approval.
- [ ] Task: Verify the live URL and commit updated state.
