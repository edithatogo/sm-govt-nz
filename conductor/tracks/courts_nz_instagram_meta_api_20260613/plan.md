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
- [x] Task: Implement an Instagram adapter behind `instagram.enabled`.
- [x] Task: Add separate duplicate-prevention state.
- [x] Task: Add tests for media payloads, attribution, errors, and disabled
  default behavior.

Evidence:
- `src.syndication.InstagramAdapter` builds Meta Instagram `/media` creation
  requests and `/media_publish` requests using `INSTAGRAM_USER_ID` and
  `INSTAGRAM_ACCESS_TOKEN`.
- The adapter is only constructed by `build_adapters_from_env(["instagram"])`
  when Instagram credentials exist; `config.json` keeps `instagram.enabled`
  false and leaves launch gated by `threads_launch_complete`.
- Duplicate prevention reuses the existing per-target
  `conductor/target_delivery_state.json` structure, keyed separately under
  `delivered_post_ids.instagram`.
- `python -m pytest tests\test_syndication.py tests\test_instagram_api_probe.py`
  passed with 24 tests.
- Direct runner smoke check returned `1 2 post-1 ['post-1']`, confirming one
  fetched post, two target deliveries, source-state advancement to `post-1`,
  and Instagram delivery-state recording under its own target key.

## Phase 4: Controlled Launch
- [ ] Task: Run a dry-run mapping for the latest Courts source post.
- [ ] Task: Review payload and account identity.
- [ ] Task: Run one controlled live post only after approval.
- [ ] Task: Verify public URL and commit state.
