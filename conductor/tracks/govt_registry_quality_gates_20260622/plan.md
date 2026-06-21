# Plan - Registry Provenance and Batch Quality Gates

## Phase 1: Baseline Integrity
- [ ] Task: Record current strict gap baseline and confirm zero unknown parties, leaders, presidents, and role organizations.
- [ ] Task: Add a regression test for known canonical role organization IDs (`the-treasury`, `mbie`, `nz-police`).

## Phase 2: Evidence Metadata
- [ ] Task: Extend agency, party, and person social profile schemas with evidence metadata fields.
- [ ] Task: Update existing registry data or schema defaults so current records remain valid.
- [ ] Task: Add tests for valid and invalid evidence metadata.

## Phase 3: Batch Gate
- [ ] Task: Update `scripts/add_person_record.py` to reject unknown role organizations before append.
- [ ] Task: Add batch validation tests for duplicate IDs, unknown organizations, invalid evidence, dry-run, and validate-only modes.
- [ ] Task: Document batch acceptance commands in the expansion track.

## Phase 4: Recomputed Gap Gate
- [ ] Task: Update `scripts/check_parties_persons_gaps.py` to recompute from current registry files by default or behind a strict option.
- [ ] Task: Preserve JSON summary output for CI and Conductor reports.
- [ ] Task: Add tests proving stale checked-in reports cannot hide current registry drift.

## Verification
- [ ] Task: Run focused registry tests.
- [ ] Task: Run strict gap checker with zero tolerances.
- [ ] Task: Update `conductor/tracks.md` and `conductor/setup_state.json`.
