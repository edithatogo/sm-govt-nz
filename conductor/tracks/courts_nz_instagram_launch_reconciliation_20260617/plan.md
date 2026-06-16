# Plan - Courts of New Zealand Instagram Launch Reconciliation

## Phase 1: Runtime Audit
- [ ] Task: Compare `config.json`, `conductor/target_delivery_state.json`, recent
  workflow runs, and Instagram track notes.
- [ ] Task: Determine whether the earlier launch notes reflected a temporary
  branch/run, an uncommitted reversal, or stale documentation.
- [ ] Task: Update the older Instagram track with a reconciliation note.

## Phase 2: Credential and Identity Check
- [ ] Task: Run `validate_instagram` or the local Instagram probe without
  posting.
- [ ] Task: Confirm the profile URL and account handle are the dedicated Courts
  mirror account.
- [ ] Task: Confirm no personal Instagram identity is used for posting.

## Phase 3: Relaunch or Defer
- [ ] Task: If credentials and identity are valid, run a dry-run latest-post
  payload review.
- [ ] Task: If approved, enable Instagram with `max_posts_per_run: 1`, add it to
  `syndicate_to`, and run one controlled live post.
- [ ] Task: If blocked, leave Instagram disabled and record the precise blocker.

## Phase 4: Closeout
- [ ] Task: Verify public delivery URL or defer status.
- [ ] Task: Commit config/state/track changes.
- [ ] Task: Update `conductor/tracks.md` and platform status review.

Current runtime status: `instagram.enabled` is false and `instagram` is not in
`monitored_accounts[0].syndicate_to`, so Instagram is not live.
