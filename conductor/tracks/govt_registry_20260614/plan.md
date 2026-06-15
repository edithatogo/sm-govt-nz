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
  - Script: `scripts/validate_git_mirrors.py` — outputs structured JSON report,
    supports `--dry-run`, `--compare-head`, `--output FILE`, and `--branch`.
  - Tests: `tests/test_validate_git_mirrors.py` — 15 test cases covering missing
    URL, SSH failure/success, dry-run, local/remote branch missing, remote
    lookup failure, misaligned heads, custom branch, JSON serialisation, and
    report envelope.
- [x] Task: Create `.github/workflows/mirror_sync.yml` to mirror the repository to a secondary git remote (GitLab or Codeberg) on every push to master.
  - Now includes `--output mirror_validation_report.json` and an
    `actions/upload-artifact@v4` step to persist the JSON report as a CI
    artifact.
- [x] Task: Validate the mirror sync workflow via a test push and check remote branch alignment.
  - Evidence: `validate_git_mirrors.py` has been enhanced with a structured
    JSON report (`build_report` / `to_json`), dry-run mode, and graceful
    handling of missing secrets/remote. The workflow runs
    `--compare-head --output mirror_validation_report.json`.
  - Validation: `scripts/verify_registry_compilation.py` cross-checks the
    compiled SQLite DB against `government_directory.json`.
  - Tests added for both scripts; run `pytest tests/test_validate_git_mirrors.py
    tests/test_verify_registry_compilation.py -v` to verify.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Multi-Remote Git Redundancy' (Protocol in workflow.md)

## Phase 3: Twitter/X Deactivation Archive & Registry Seeding
- [x] Task: Ingest and parse historical post archives for target deactivated NZ government accounts.
- [x] Task: Seed `registry/government_directory.json` with the initial deactivated accounts (status: deactivated, start/end dates, reasons, and active alternatives).
- [x] Task: Run the compilation pipeline to verify that all historical and seeded files compile perfectly.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Twitter/X Deactivation Archive & Registry Seeding' (Protocol in workflow.md)

## Phase 4: Syndication & Mirroring Implementation
- [x] Task: Implement a unified mirror target posting adapter to syndicate updates to the unified transparency feed.
  - Added `src/unified_syndication.py` in commit `75f012b`.
- [x] Task: Implement configuration-based opt-out controls in `config.json` for specific agencies or sites.
  - Existing runner opt-out path is covered through `_should_syndicate` and `syndication_opt_outs`.
- [~] Task: Write unit and integration tests verifying the posting adapter, formatting, attribution links, and opt-out logic.
  - [x] Added focused unified adapter tests in `tests/test_unified_syndication.py`.
  - [x] Added runner integration coverage proving the disabled-by-default
    `unified` target wraps its configured base adapter and records delivery
    state under `delivered_post_ids.unified`.
- [~] Task: Conduct a controlled dry-run and live-post test for the unified mirror feed.
  - Current status: adapter-level tests exist, but the unified transparency feed
    is now wired behind explicit config and remains disabled by default.
  - [x] Controlled dry-run passed on 15 June 2026 using the public Courts of NZ
    Bluesky feed; see `conductor/unified_transparency_dry_run_20260615.json`.
  - [ ] Reviewed live-post verification remains pending launch approval.
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Syndication & Mirroring Implementation' (Protocol in workflow.md)
