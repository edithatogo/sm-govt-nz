# Plan - Registry Verification Refresh Cadence

## Phase 1: Metadata Model
- [ ] Task: Decide whether refresh metadata lives inline on profile records or in a companion report file.
- [ ] Task: Add `last_checked_at`, `last_seen_at`, and `verification_status` support where needed.
- [ ] Task: Add schema tests for refresh metadata.

## Phase 2: Refresh Report
- [ ] Task: Implement a non-mutating report command for stale and due-for-review records.
- [ ] Task: Group report output by agencies, parties, MPs, public sector leaders, and historical figures.
- [ ] Task: Add tests for monthly, event-triggered, and annual cadence calculations.

## Phase 3: Conductor Operations
- [ ] Task: Document refresh cadence in the active registry expansion track.
- [ ] Task: Add report artifact path under `conductor/`.
- [ ] Task: Add CI or manual workflow guidance after the report command is stable.

## Verification
- [ ] Task: Run focused refresh report tests.
- [ ] Task: Run registry schema tests.
- [ ] Task: Update `conductor/tracks.md` and `conductor/setup_state.json`.
