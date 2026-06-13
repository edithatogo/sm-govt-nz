# Plan - Courts of New Zealand Bluesky Archive Replay

## Phase 1: Coverage Baseline
- [x] Task: Add archive mirror coverage reporting for Bluesky and X source
  archives.
- [x] Task: Seed bounded X archive replay to the Bluesky mirror pipeline.
- [x] Task: Verify first X archive replay post on the public Bluesky mirror.

## Phase 2: Replay Completion
- [ ] Task: Continue bounded Bluesky-source backlog runs until
  `conductor/bluesky_backlog_state.json` reaches 49 source records.
- [ ] Task: Continue bounded X archive replay runs until
  `conductor/archive_mirror_state.json` reaches 689 recovered X records.
- [ ] Task: Increase or tune batch size only after reviewing account-rate,
  platform-noise, and duplicate-prevention behavior.
- [ ] Task: Re-run coverage reporting after each phase and commit state.

## Phase 3: Manifest and Verification
- [ ] Task: Extend the corpus manifest with source record ID, source URL,
  original timestamp, mirror target, and mirror URL.
- [ ] Task: Verify a sample of Bluesky-source and X-source mirror URLs via the
  public Bluesky API.
- [ ] Task: Mark any unreplayable records with reason codes.

## Phase 4: Closeout
- [ ] Task: Run full tests and CI.
- [ ] Task: Update the parent Bluesky mirror track and archive/corpus tracks.
