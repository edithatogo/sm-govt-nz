# Plan - Courts of New Zealand Bluesky Archive Replay

## Phase 1: Coverage Baseline
- [x] Task: Add archive mirror coverage reporting for Bluesky and X source
  archives.
- [x] Task: Seed bounded X archive replay to the Bluesky mirror pipeline.
- [x] Task: Verify first X archive replay post on the public Bluesky mirror.

## Phase 2: Replay Completion
- [x] Task: Continue bounded Bluesky-source backlog runs until
  `conductor/bluesky_backlog_state.json` reaches 49 source records.
  - Verified dry-run selected 0 remaining Bluesky backlog records.
- [ ] Task: Continue bounded X archive replay runs until
  `conductor/archive_mirror_state.json` reaches 689 recovered X records.
  - Live run `27500249516` posted 5 X archive records to the Bluesky mirror
    and captured delivery URLs in `conductor/archive_mirror_state.json`.
  - Live run `27500580864` posted another 5 X archive records, verified the
    last 5 delivery URLs, and committed state update `5d46500`.
  - Added a manual-only `Archive Replay` workflow so reviewed batches can run at
    5, 10, or 20 records without increasing the scheduled `Syndicate` throttle.
- [ ] Task: Increase or tune batch size only after reviewing account-rate,
  platform-noise, and duplicate-prevention behavior.
- [x] Task: Re-run coverage reporting after each phase and commit state.
  - Latest coverage shows Bluesky target at 182/738 total source records, with
    0 remaining Bluesky-source records and 556 remaining X archive records.

## Phase 3: Manifest and Verification
- [x] Task: Extend the corpus manifest with source record ID, source URL,
  original timestamp, mirror target, and mirror URL.
  - Added `record_index` to `corpus_manifest.json`; older replay state does
    not retain mirror URLs, so the field is present and empty where unavailable.
  - Future archive replay deliveries now record delivery details and derived
    Bluesky mirror URLs in `conductor/archive_mirror_state.json`.
- [x] Task: Verify a sample of Bluesky-source and X-source mirror URLs via the
  public Bluesky API.
  - Added `scripts/verify_archive_mirror_posts.py` and wired it into
    `Syndicate`; local read-only verification passed for the five URL-bearing
    archive replay deliveries from run `27500249516`.
  - Workflow run `27500580864` verified 5 archive mirror posts through the
    public Bluesky API before committing state.
- [ ] Task: Mark any unreplayable records with reason codes.

## Phase 4: Closeout
- [ ] Task: Run full tests and CI.
- [ ] Task: Update the parent Bluesky mirror track and archive/corpus tracks.
