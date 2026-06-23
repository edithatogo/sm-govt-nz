# Plan — NZ Government Social Media Registry Full Expansion

## Scope
- Complete persons registry covering all current 54th Parliament MPs (~123)
- Full social profiles (X/Twitter, Facebook, Instagram, LinkedIn, etc.)
- Historical figures working backwards (PMs, leaders, and notable figures)
- Public sector leaders (constitutional officers, agency CEOs, judges)
- Syndication classification per account
- Tenure-linked profiles
- Quality gates, refresh cadence, and account classification taxonomy are tracked
  separately in the 2026-06-22 Conductor tracks listed in `conductor/tracks.md`.

## Phases

### Phase 0: Tooling & Track Setup
- [x] Task: Create `scripts/add_person_record.py` — batch person record adder with schema validation
- [x] Task: Create `scripts/data/` directory for batch input files
- [x] Task: Create track directory with spec, plan, metadata, pending checklist
- [x] Task: Update `conductor/tracks.md` with new track entry

### Phase 1: National Party Caucus — Batch 1 (Cabinet & Senior Ministers)
- [x] Task: Research social profiles for first 16 National MPs (Cabinet + ministers outside Cabinet)
- [x] Task: Create `scripts/data/national_batch_1.json` with 16 person records
- [x] Task: Validate and append to `registry/persons.json` using add_person_record.py
- [x] Task: Run gap checker and tests — all clean
- [x] Task: Commit batch 1 with message `national_batch_1: add 16 National MPs` (`dfcdee0`)

### Phase 1: National Party Caucus — Batch 2 (Remaining Electorate MPs)
- [x] Task: Research social profiles for next 14 National electorate MPs
- [x] Task: Create `scripts/data/national_batch_2.json` with records
- [x] Task: Validate, append, verify, commit (`e991d9e`)

### Phase 1: National Party Caucus — Batch 3 (Remaining List & Junior MPs)
- [x] Task: Research and add remaining 12 National MPs
- [x] Task: Validate, append, verify, commit (`928a675`)
- [ ] Task: Push Phase 1/current-MP roster updates to remote, verify GitHub Actions (pending explicit remote approval).

### Phase 2: Labour Party Caucus
- [x] Task: Confirm `govt_registry_quality_gates_20260622` Phase 1 gates are in place before appending new Labour records.
- [x] Task: Research and fill blank social profile handles; zero blank handles remain, and unresolved current-MP empty profiles are reviewed in `conductor/current_mp_social_profile_review_20260623.json`.
- [x] Task: Research current Labour roster replacements and add 22 missing Labour MP records.
- [x] Task: Validate, append, and verify current-MP roster gap batch locally.
- [ ] Task: Push Phase 2/current-MP roster updates to remote, verify GitHub Actions (pending explicit remote approval)

### Phase 3: Green Party Caucus (15 MPs)
- [ ] Task: Research all Green MPs — records and social profiles
- [x] Task: Add missing Green records and structured profiles/reviewed empty-profile artifact.
- [x] Task: Validate, append, and verify current-MP records locally.
- [ ] Task: Push current-MP roster updates to remote, verify GitHub Actions (pending explicit remote approval)

### Phase 4: ACT Party Caucus (11 MPs)
- [ ] Task: Research all ACT MPs — 9 new records + profiles
- [x] Task: Validate, append, and verify current-MP records locally.
- [ ] Task: Push current-MP roster updates to remote, verify GitHub Actions (pending explicit remote approval)

### Phase 5: NZ First Caucus (8 MPs)
- [ ] Task: Research all NZ First MPs — 6 new records + profiles
- [x] Task: Validate, append, and verify current-MP records locally.
- [ ] Task: Push current-MP roster updates to remote, verify GitHub Actions (pending explicit remote approval)

### Phase 6: Te Pāti Māori Caucus (6 MPs)
- [ ] Task: Research all Te Pāti Māori MPs — 3 new records + profiles
- [x] Task: Validate, append, and verify current-MP records locally.
- [ ] Task: Push current-MP roster updates to remote, verify GitHub Actions (pending explicit remote approval)

### Phase 7: Historical Figures (Working Backwards)
- [ ] Task: Add former Prime Ministers (Key, English, Ardern, Clark, etc.)
- [ ] Task: Add former Deputy PMs and senior ministers
- [ ] Task: Add historical party leaders from 1990s onward
- [ ] Task: Add other notable historical figures with social media presence
- [ ] Task: Validate, commit per batch, push per group

### Phase 8: Public Sector Leaders
- [ ] Task: Governor-General, Speaker
- [ ] Task: Commissioners (Privacy, HRC, Children's, Health & Disability, PCE)
- [ ] Task: Ombudsmen, Auditor-General, Reserve Bank Governor
- [ ] Task: Police Commissioner, Defence Chief
- [ ] Task: Agency Chief Executives (major departments)
- [ ] Task: Senior Judiciary (Chief Justice, Supreme Court, Court of Appeal)
- [ ] Task: Validate, commit per group, push

### Phase 9: Syndication Classification
- [x] Task: Hand off to `govt_registry_account_classification_20260622` for classification schema and taxonomy.
- [x] Task: Apply classification data after taxonomy and tests are accepted for the current seeded registry.

### Phase 10: Tenure-Linked Profiles
- [x] Task: Populate tenure_linked_profiles for all persons with tracked role-based accounts after classification taxonomy is accepted for the current seeded registry.
- [ ] Task: Validate, commit, push

### Phase 11: Final Verification & Close
- [ ] Task: Final strict CI gate — all gaps zero
- [ ] Task: Verify GitHub Actions passes
- [ ] Task: Update tracks.md — mark track complete
- [ ] Task: Archive gap report to conductor/

## Workflow
1. Research handles via parliament.nz, wheretheystand.nz, party websites, direct platform search
2. Create batch JSON file in scripts/data/
3. Run `python scripts/add_person_record.py -i scripts/data/[batch].json`
4. Run `python scripts/check_parties_persons_gaps.py --strict`
5. Run `python scripts/report_refresh_cadence.py --as-of YYYY-MM-DD --output conductor/registry_refresh_report.json`
6. Run `python -m pytest tests/test_parties_persons_registry.py -v`
7. `git add -A && git commit -m "phaseX_batchY: description"`
8. Repeat per logical task
9. Per phase: `git push` and verify GitHub Actions

## Current Status
- National Party Phase 1 data batches 1-3 are committed and reference-integrity clean.
- Current strict gap gate passes with zero missing party leaders, missing party presidents, unknown party references, and unknown role organization references.
- Refresh cadence is implemented in `govt_registry_refresh_cadence_20260622`;
  `conductor/registry_refresh_report.json` is the manual refresh queue artifact.
  Initial 2026-06-22 queue: agencies first, with 483 profiles due across 218
  agency records because `last_checked_at` has not yet been populated.
- Account classification is implemented in `govt_registry_account_classification_20260622`;
  future seeded profiles must include `account_classification` and
  `syndication_classification`, and role-linked accounts must reference an
  existing `role_id`.
- Current-MP roster batches are locally complete. Next local data-coverage work is Phase 7 historical figures and Phase 8 public-sector leaders; remote push/GitHub Actions verification requires explicit approval.

- Quality-gates track is complete: evidence metadata is optional but validated when present, append batches reject unknown role organizations, and the strict gap gate recomputes from current registry files by default.

- Current-MP roster gap closure (2026-06-23): appended 60 records from
  `scripts/data/current_mp_roster_gap_batch_20260623.json`; persons registry now
  has 159 records. Current-MP coverage floors pass for National, Labour, Greens,
  ACT, NZ First, and Te Pati Maori. Blank social handles are zero. Remaining
  current MPs without structured social IDs are explicitly reviewed in
  `conductor/current_mp_social_profile_review_20260623.json`.
- Verification (2026-06-23): `python scripts/check_parties_persons_gaps.py --strict --allow-leaders 0 --allow-presidents 0 --write-report`; `python -m pytest -q --basetemp=.tmp/pytest-current-mp-expansion-20260623b tests/test_parties_persons_registry.py tests/test_registry_schema.py tests/test_add_person_record.py tests/test_check_parties_persons_gaps.py`; `ruff check --no-cache tests/test_parties_persons_registry.py tests/test_registry_schema.py tests/test_add_person_record.py tests/test_check_parties_persons_gaps.py scripts/add_person_record.py scripts/check_parties_persons_gaps.py`.
- Remaining track scope: remote push/GitHub Actions verification requires explicit
  approval; Phase 7 historical figures and Phase 8 public-sector leader expansion
  remain the next local data-coverage work.
