# Plan - Courts of New Zealand Bluesky Profile Archive

## Phase 1: Evidence Capture
- [ ] Task: Fetch source Bluesky profile metadata and asset URLs.
- [ ] Task: Fetch mirror Bluesky profile metadata and asset URLs.
- [ ] Task: Save dated JSON snapshots under `profile_archive/courts-nz/`.
- [ ] Task: Download avatar and banner assets where public URLs are available.

## Phase 2: Identity Review
- [ ] Task: Compare source and mirror profiles against the mirror identity
  contract.
- [ ] Task: Record any profile-field gaps as follow-up tasks without changing
  account settings automatically.
- [ ] Task: Commit profile evidence after review.

## Phase 3: Track Closeout
- [ ] Task: Update the parent Bluesky mirror track once evidence is complete.
- [ ] Task: Run tests or lint only if docs/scripts changed.
