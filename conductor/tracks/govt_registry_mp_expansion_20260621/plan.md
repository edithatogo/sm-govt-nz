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
- [ ] Task: Push Phase 1 to remote, verify GitHub Actions

### Phase 2: Labour Party Caucus
- [ ] Task: Confirm `govt_registry_quality_gates_20260622` Phase 1 gates are in place before appending new Labour records.
- [ ] Task: Research and fill 38 empty social profile handles
- [ ] Task: Research remaining ~20 Labour MPs and add records
- [ ] Task: Validate, append, verify, commit
- [ ] Task: Push Phase 2 to remote, verify GitHub Actions

### Phase 3: Green Party Caucus (15 MPs)
- [ ] Task: Research all Green MPs — records and social profiles
- [ ] Task: Add 11 new records + fill profiles
- [ ] Task: Validate, append, verify, commit, push

### Phase 4: ACT Party Caucus (11 MPs)
- [ ] Task: Research all ACT MPs — 9 new records + profiles
- [ ] Task: Validate, append, verify, commit, push

### Phase 5: NZ First Caucus (8 MPs)
- [ ] Task: Research all NZ First MPs — 6 new records + profiles
- [ ] Task: Validate, append, verify, commit, push

### Phase 6: Te Pāti Māori Caucus (6 MPs)
- [ ] Task: Research all Te Pāti Māori MPs — 3 new records + profiles
- [ ] Task: Validate, append, verify, commit, push

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
- [ ] Task: Hand off to `govt_registry_account_classification_20260622` for classification schema and taxonomy.
- [ ] Task: Apply classification data after taxonomy and tests are accepted.

### Phase 10: Tenure-Linked Profiles
- [ ] Task: Populate tenure_linked_profiles for all persons with tracked role-based accounts after classification taxonomy is accepted.
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
5. Run `python -m pytest tests/test_parties_persons_registry.py -v`
6. `git add -A && git commit -m "phaseX_batchY: description"`
7. Repeat per logical task
8. Per phase: `git push` and verify GitHub Actions

## Current Status
- National Party Phase 1 data batches 1-3 are committed and reference-integrity clean.
- Current strict gap gate passes with zero missing party leaders, missing party presidents, unknown party references, and unknown role organization references.
- Next coverage batch is Labour, but it should wait until the quality-gates track defines the evidence/provenance fields and strict batch checks.
