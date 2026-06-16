# Plan - Courts of New Zealand X/Twitter Launch Route

## Phase 1: Route Decision
- [ ] Task: Review the existing X adapter, Buffer integration notes, and current
  GitHub secrets to identify which route is actually available.
- [ ] Task: Confirm whether the chosen route has a usable free tier, posting
  entitlement, and token lifetime suitable for scheduled mirror posting.
- [ ] Task: Record route decision, costs, expiry, queue behavior, and fallback
  policy in this track.

## Phase 2: Validation
- [ ] Task: Add or update a non-posting credential probe for the selected route.
- [ ] Task: Add secret validation for the selected route, including expiry where
  available.
- [ ] Task: Run a dry-run latest-post mapping with tokens redacted.
- [ ] Task: Confirm no personal account identity enters payloads or state.

## Phase 3: Controlled Launch
- [ ] Task: Add `x` to the Courts of New Zealand `syndicate_to` list only after
  validation passes.
- [ ] Task: Set `syndication_targets.x.enabled` to true with
  `max_posts_per_run: 1`.
- [ ] Task: Run one controlled live post.
- [ ] Task: Verify the public X URL and commit delivery state.

## Phase 4: Operations
- [ ] Task: Add scheduled validation and token-expiry monitoring for the selected
  route.
- [ ] Task: Add failure isolation so a broken X route cannot block Bluesky,
  Threads, archive capture, or dataset publication.
- [ ] Task: Review the first scheduled successful run before marking complete.

Current runtime status: `x.enabled` is false and `x` is not in
`monitored_accounts[0].syndicate_to`, so X/Twitter is not live.
