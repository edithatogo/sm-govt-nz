# Plan - Courts of New Zealand Threads Adapter Launch

## Phase 1: Adapter Contract
- [x] Task: Define Threads payload builder for text-only and media posts.
- [x] Task: Add a Threads adapter class with injected HTTP client for tests.
- [x] Task: Keep the adapter unreachable unless `threads.enabled` is true.

## Phase 2: State and Tests
- [ ] Task: Add Threads duplicate-prevention state.
- [x] Task: Add unit tests for formatting, attribution, state, and API errors.
- [ ] Task: Add guardrail tests proving archive replay is not used by default.

## Phase 3: Dry Run
- [ ] Task: Add a dry-run command for the latest source post.
- [ ] Task: Review generated payload against Threads limits and identity rules.
- [ ] Task: Confirm no LinkedIn or personal identity data enters the payload.

## Phase 4: Controlled Live Launch
- [ ] Task: Enable Threads for a one-post manual workflow dispatch.
- [ ] Task: Verify public Threads URL and commit state.
- [ ] Task: Disable or retain scheduling according to launch review.
