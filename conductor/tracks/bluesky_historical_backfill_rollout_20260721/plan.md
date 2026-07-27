# Plan

- [x] Implement serial four-per-day backfill and account audit state.
- [x] Add historical attribution and public-readback requirements.
- [ ] Repair and observe the Courts canary.
- [ ] Select and observe two smallest-backlog pilots.
- [ ] Continue sequential rollout until all eligible identities are live, complete, or evidence-backed terminal.

## Pilot selection snapshot (2026-07-27)

- ACC is the first live pilot; cleanup and post-remediation observation remain open.
- `conductor/bluesky_mirror_pilot_candidates.json` applies
  `eligible_backlog_ascending_then_mirror_id` to the fail-closed source contract.
- Electoral Commission (`#85`) is the next operator-supervised pilot with one
  eligible unique record. Account registration, profile configuration,
  credentials, preflight, and posting remain separate operator gates.
