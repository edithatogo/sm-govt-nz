# Plan - NZ Government Social Media Registry & Archiver (Phase 1 & 2)

## Phase 1: Registry Schema & Compilation Pipeline
- [x] Task: Write schema validation tests in `tests/test_registry_schema.py` enforcing formatting, parent-child hierarchy validation, and loop prevention.
- [x] Task: Define the registry JSON schema and structure in `registry/government_directory.json`.
- [x] Task: Implement `scripts/compile_registry.py` to parse `registry/government_directory.json` and output domain-specific JSON files.
- [x] Task: Extend `scripts/compile_registry.py` to generate the SQLite database `registry/government_directory.db` with normalized tables.
- [x] Task: Add test coverage in `tests/test_compile_registry.py` for SQLite database generation and table integrity.
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Registry Schema & Compilation Pipeline' (Protocol in workflow.md)

## Phase 2: Multi-Remote Git Redundancy
- [x] Task: Write a check script to verify SSH/Access key validation for secondary Git hosts.
- [x] Task: Create `.github/workflows/mirror_sync.yml` to mirror the repository to a secondary git remote (GitLab or Codeberg) on every push to master.
- [ ] Task: Validate the mirror sync workflow via a test push and check remote branch alignment.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Multi-Remote Git Redundancy' (Protocol in workflow.md)

## Phase 3: Twitter/X Deactivation Archive & Registry Seeding
- [x] Task: Ingest and parse historical post archives for target deactivated NZ government accounts.
- [x] Task: Seed `registry/government_directory.json` with the initial deactivated accounts (status: deactivated, start/end dates, reasons, and active alternatives).
- [x] Task: Run the compilation pipeline to verify that all historical and seeded files compile perfectly.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Twitter/X Deactivation Archive & Registry Seeding' (Protocol in workflow.md)

## Phase 4: Syndication & Mirroring Implementation
- [ ] Task: Implement a unified mirror target posting adapter to syndicate updates to the unified transparency feed.
- [ ] Task: Implement configuration-based opt-out controls in `config.json` for specific agencies or sites.
- [ ] Task: Write unit and integration tests verifying the posting adapter, formatting, attribution links, and opt-out logic.
- [ ] Task: Conduct a controlled dry-run and live-post test for the unified mirror feed.
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Syndication & Mirroring Implementation' (Protocol in workflow.md)
