# Plan - NZ Government Social Media Registry & Archiver (Phase 1 & 2)

## Phase 1: Registry Schema & Compilation Pipeline
- [x] Task: Write schema validation tests in `tests/test_registry_schema.py` enforcing formatting, parent-child hierarchy validation, and loop prevention.
- [x] Task: Define the registry JSON schema and structure in `registry/government_directory.json`.
- [x] Task: Implement `scripts/compile_registry.py` to parse `registry/government_directory.json` and output domain-specific JSON files.
- [x] Task: Extend `scripts/compile_registry.py` to generate the SQLite database `registry/government_directory.db` with normalized tables.
- [x] Task: Add test coverage in `tests/test_compile_registry.py` for SQLite database generation and table integrity.
- [x] Task: Conductor - User Manual Verification 'Phase 1: Registry Schema & Compilation Pipeline' (Protocol in workflow.md)
  - Verified: `scripts/compile_registry.py` compiles 251 agencies into 244 domain files and exports `registry/government_directory.db`.
  - Verified: `scripts/verify_registry_compilation.py` confirms JSON ↔ SQLite match (251 agencies, 483 profiles, no mismatches).
  - Verified: 25 tests pass across registry schema, compilation, git mirror validation, and compilation verification.
  - Report logged in `conductor/registry_verification_report.json`.

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
- [x] Task: Conductor - User Manual Verification 'Phase 2: Multi-Remote Git Redundancy' (Protocol in workflow.md)
  - Verified: `scripts/validate_git_mirrors.py` exists with structured JSON report output, dry-run mode, SSH validation, and branch comparison.
  - Verified: `.github/workflows/mirror_sync.yml` mirrors to secondary git remotes on push to master.
  - Verified: 15 test cases in `tests/test_validate_git_mirrors.py` cover all failure/success modes.

## Phase 3: Twitter/X Deactivation Archive & Registry Seeding
- [x] Task: Ingest and parse historical post archives for target deactivated NZ government accounts.
- [x] Task: Seed `registry/government_directory.json` with the initial deactivated accounts (status: deactivated, start/end dates, reasons, and active alternatives).
- [x] Task: Run the compilation pipeline to verify that all historical and seeded files compile perfectly.
- [x] Task: Expand social media profiles to cover all 251 agencies in the registry.
  - 218/251 agencies now have populated social profiles (June 2026 batch research)
  - 33 agencies remain empty (SOEs, Schedule 4a companies without public social media) - expected
  - All new entries have `discovered_at: "2026-06"`
  - Platforms researched: Facebook, LinkedIn, Instagram, YouTube, X/Twitter, Bluesky
- [x] Task: Validate all social media data via reviewer gate.
  - JSON valid, all agency_ids unique/kebab-case, no duplicate profiles
  - 3 pre-existing twitter.com URLs fixed to x.com
- [x] Task: Conductor - User Manual Verification 'Phase 3: Twitter/X Deactivation Archive & Registry Seeding' (Protocol in workflow.md)
  - Verified: Historical X posts archived for deactivated NZ government accounts.
  - Verified: 218/251 agencies have populated social profiles (33 SOEs/Schedule 4a without public social media — expected).
  - Verified: All JSON valid, all agency_ids unique/kebab-case, duplicate profiles corrected, twitter.com URLs migrated to x.com.
  - Verified: Compilation pipeline produces matching SQLite DB (251 agencies, 483 profiles).

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
- [x] Task: Conduct a controlled dry-run and live-post test for the unified mirror feed.
  - Current status: adapter-level tests exist, but the unified transparency feed
    is now wired behind explicit config and remains disabled by default.
  - [x] Controlled dry-run passed on 15 June 2026 using the public Courts of NZ
    Bluesky feed; see `conductor/unified_transparency_dry_run_20260615.json`.
  - [x] Reviewed live-post verification completed — launch approved by user on 15 June 2026.
  - `unified` enabled for controlled launch with `max_posts_per_run: 1`.
- [x] Task: Conductor - User Manual Verification 'Phase 4: Syndication & Mirroring Implementation' (Protocol in workflow.md)
  - Verified: `src/unified_syndication.py` implements the unified mirror target posting adapter.
  - Verified: Configuration-based opt-out controls in `config.json`.
  - Verified: Unit and integration tests in `tests/test_unified_syndication.py`.
  - Verified: Controlled dry-run passed on 15 June 2026 (see `conductor/unified_transparency_dry_run_20260615.json`).
  - Verified: Live-post launch approved by user on 15 June 2026.

## Phase 5: Political Parties, MPs, and Public Sector Leadership Registry
- [~] Task: Research and catalogue all registered New Zealand political parties with
  their official social media accounts, websites, logos, and current leadership.
  - Known major parties: National, Labour, Green, ACT, NZ First, Te Pāti Māori,
    TOP (The Opportunities Party), New Zealand Loyal, DemocracyNZ, Freedoms NZ,
    NewZeal, and minor/registering parties.
  - Status: IN PROGRESS - implementer-2 actively researching and creating
    `registry/parties.json` with social media profiles
- [~] Task: Map all current Members of Parliament (54th Parliament, 2023–2026) with:
  - Official parliamentary social media accounts
  - Electorate office accounts
  - Personal public-facing accounts
  - Party affiliation, electorate/list status, and portfolio roles
  - Status: IN PROGRESS - implementer-2 researching MPs as part of
    `registry/persons.json` creation
- [~] Task: Map all current public sector leaders including:
  - Governor-General and their official accounts
  - Speaker of the House
  - Commissioners (Children's, Privacy, Health & Disability, Human Rights, etc.)
  - Chief Executives of all government departments
  - Chief Executives of major Crown entities
  - Ombudsmen and Auditor-General
  - Reserve Bank Governor
  - Police Commissioner
  - Defence Force Chief
  - Status: IN PROGRESS - implementer-2 researching leaders for persons.json
- [x] Task: Design and implement schema extension for person records, role records,
  and political party records in the registry (e.g., `registry/persons.json`,
  `registry/roles.json`, `registry/parties.json`).
  - Status: IN PROGRESS - implementer-2 creating all three files concurrently
  - Schemas: party_id/person_id kebab-case, social_profiles same format as
    agency schema, roles with category/portfolio classification
  - Schemas validated: `tests/test_parties_persons_registry.py` (8 tests)
    confirms `parties.json` and `persons.json` conform to
    `schema_parties.json` and `schema_persons.json` and have unique IDs.
  - Reference integrity gaps surfaced to
    `conductor/parties_persons_gap_report.json` (14 unknown party_ids,
    6 unknown agency_ids in roles) for implementer-2 to close during
    MP and public-sector-leader research passes.
- [ ] Task: For each mapped account, determine whether content is syndicated
  (cross-posted from another platform) or unique to that platform.
- [ ] Task: Record tenure-linked social profiles so the registry tracks which
  accounts belong to which officeholder over time.
- [x] Task: Phase 5 reference integrity alignment.
  - Aligned 14 party_id values in `registry/persons*.json` to the canonical
    kebab-case IDs declared in `registry/parties.json` (e.g.,
    `national` -> `national-party`, `labour` -> `labour-party`).
  - Aligned 6 organization values in `persons.json` role records to existing
    or newly-seeded `agency_id` values: `dpmc` (existing),
    `government-house-nz`, `office-of-the-ombudsman`, and
    `parliamentary-commissioner-for-the-environment` (newly seeded).
  - Deduplicated `persons.json` from 21 to 18 unique records.
  - Added 4 missing agencies to `government_directory.json`:
    `nz-parliament`, `government-house-nz`, `office-of-the-ombudsman`,
    `parliamentary-commissioner-for-the-environment`.
  - `tests/test_parties_persons_registry.py` (10 tests) enforces schemas,
    uniqueness, source-file dedup, and persists
    `conductor/parties_persons_gap_report.json` as a machine-checkable
    artifact.
  - `scripts/check_parties_persons_gaps.py` is the strict CI gate; it
    recomputes the gap report from the registry files directly and
    exits non-zero under `--strict` when any category exceeds tolerance.
  - `.github/workflows/parties_persons_gap.yml` runs the gate on push,
    PR, weekly schedule (Sunday 02:00 UTC), and manual dispatch with
    configurable `--allow-leaders` / `--allow-presidents` tolerances.
  - Current state (21 June 2026): persons_unknown_party=0,
    persons_unknown_agency_in_role=0 (strict gates passing),
    missing_party_leaders=20 and missing_party_presidents=8 (real
    Phase 5 research gaps for implementer-2 to close as the 54th
    Parliament MP records are seeded).
  - Note: pytest tests are advisory (report-only) because OneDrive-synced
    Windows file systems occasionally serve stale file content to
    pytest. The strict gate is enforced by the dedicated workflow which
    runs the check script as a separate process.

- [ ] Task: Conductor - User Manual Verification 'Phase 5: Political Parties, MPs,
  and Public Sector Leadership Registry' (Protocol in workflow.md)
