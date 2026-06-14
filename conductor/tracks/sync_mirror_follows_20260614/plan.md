# Plan - Automated Bi-Directional Mirror Follow Sync (Phase 1, 2 & 3)

## Phase 1: Relationship Mapping & Read Probes
- [ ] Task: Write tests in `tests/test_follow_matrix.py` to verify follow matrix generation and loop prevention.
- [ ] Task: Implement follow-checking probes in `scripts/check_follow_status.py` for Twitter/X, Bluesky, Threads, and Instagram.
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Relationship Mapping & Read Probes' (Protocol in workflow.md)

## Phase 2: Archiving & Follow State Cache
- [ ] Task: Define the schema and initialize `conductor/follow_sync_state.json`.
- [ ] Task: Write scripts to serialize/deserialize Playwright browser sessions and cookies securely.
- [ ] Task: Add test suite coverage for follow state updates and caching logic.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Archiving & Follow State Cache' (Protocol in workflow.md)

## Phase 3: Core Group Follow Sync Execution
- [ ] Task: Implement write-follow operations in `scripts/sync_mirror_follows.py` using Bluesky AT Protocol and Twitter/X API.
- [ ] Task: Implement Playwright stealth-mode fallback follow-clicker scripts for Threads and Instagram.
- [ ] Task: Integrate `scripts/sync_mirror_follows.py` as a daily step in `.github/workflows/syndicate.yml`.
- [ ] Task: Perform a dry-run and controlled live execution test for the core mirror accounts.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Core Group Follow Sync Execution' (Protocol in workflow.md)
