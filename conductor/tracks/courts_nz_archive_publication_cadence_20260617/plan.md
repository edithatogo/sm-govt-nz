# Plan - Courts of New Zealand Archive Publication Cadence

## Phase 1: Current Behavior Audit
- [ ] Task: Review `.github/workflows/archive_sources.yml`,
  `.github/workflows/publish_archives.yml`, and
  `.github/workflows/publish_zenodo_deposition.yml`.
- [ ] Task: Confirm whether scheduled `Publish Archives` runs currently publish
  externally or only upload GitHub artifacts.
- [ ] Task: Record current Hugging Face dataset URL, Zenodo DOI, and latest
  successful publication run IDs.

## Phase 2: Hugging Face Cadence
- [ ] Task: Decide the default Hugging Face cadence for Courts of New Zealand
  archive updates.
- [ ] Task: Implement a safe scheduled Hugging Face publication path or an
  explicit manual-approval gate if automatic external publishing is not wanted.
- [ ] Task: Add a freshness report that compares the latest archive commit with
  the latest Hugging Face publication.

## Phase 3: Zenodo Cadence
- [ ] Task: Define snapshot cadence, such as monthly, milestone, or manual-only.
- [ ] Task: Keep DOI publication behind an explicit confirmation phrase or
  release-review gate.
- [ ] Task: Record the relation between GitHub archive state, Hugging Face
  rolling dataset, and Zenodo versioned snapshots.

## Phase 4: Closeout
- [ ] Task: Update multi-source archive plan and project docs with final cadence.
- [ ] Task: Run the relevant publication workflow in artifact-only mode and, if
  approved, one external publication run.
- [ ] Task: Commit publication reports and track status.

Current runtime status: archive capture is scheduled. External publication is
available, but the committed workflow still needs a reviewed cadence statement
for automatic Hugging Face updates and episodic Zenodo snapshots.
