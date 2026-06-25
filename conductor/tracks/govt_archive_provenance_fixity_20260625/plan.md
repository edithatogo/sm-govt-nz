# Plan - NZ Government Archive - provenance, fixity, and reproducible research packaging

## Dependencies
Depends on `govt_archive_external_publication_20260625`.

## Implementation Rules for Less-Capable Agents
- Start with manifest schemas before changing publication workflows.
- Keep fixity validation deterministic and local.
- Do not require live network calls for checksum or package-validation tests.
- After each phase, run `$conductor-review`, apply fixes, rerun focused tests, commit, and add a git note.

## Phase 1: Manifest Contract
- [ ] Task 1: Define raw capture checksum fields.
- [ ] Task 2: Define normalized shard checksum fields.
- [ ] Task 3: Add package-level provenance fields for capture window, generator version, source types, and publication target.
- [ ] Task 4: Add schema tests for missing and mismatched checksums.

## Phase 2: Reproducible Packaging
- [ ] Task 5: Make package ordering stable across filesystems.
- [ ] Task 6: Record tool versions and source manifests inside every bundle.
- [ ] Task 7: Add a dry-run package validation command that does not upload.

## Phase 3: Citation and Research Metadata
- [ ] Task 8: Add citation metadata for Hugging Face and Zenodo users.
- [ ] Task 9: Record DOI/version linkage when Zenodo publication is used.
- [ ] Task 10: Add release notes summarizing source counts, capture window, and exclusions.

## Phase 4: Review and Handoff
- [ ] Task 11: Run `$conductor-review` against schema, packaging, and publication tests.
- [ ] Task 12: Apply review fixes and add git notes with validation evidence.
