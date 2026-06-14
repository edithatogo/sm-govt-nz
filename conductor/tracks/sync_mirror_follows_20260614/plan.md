# Plan - Mirror Account Follow Sync

## Phase 1: Relationship Mapping & Read Probes
- [ ] Task: Write tests in `tests/test_follow_matrix.py` to verify follow matrix generation and loop prevention.
- [ ] Task: Implement read-only follow-checking probes in `scripts/check_follow_status.py` for platforms with supported public/API visibility.
- [ ] Task: Mark unsupported or auth-restricted follow checks as manual review items rather than browser automation tasks.
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Relationship Mapping & Read Probes' (Protocol in workflow.md)

## Phase 2: Archiving & Follow State Cache
- [ ] Task: Define the schema and initialize `conductor/follow_sync_state.json`.
- [ ] Task: Persist only non-secret follow status evidence, timestamps, platform identifiers, and manual-review notes.
- [ ] Task: Add test suite coverage for follow state updates and caching logic.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Archiving & Follow State Cache' (Protocol in workflow.md)

## Phase 3: Core Group Follow Sync Execution
- [ ] Task: Implement write-follow operations only for platforms with supported official APIs and explicit repository secrets.
- [ ] Task: Keep Threads, Instagram, Facebook, and any other unsupported follow paths as manual checklists unless an official API route is confirmed.
- [ ] Task: Add an opt-in manual workflow for dry-run reporting before any live follow execution.
- [ ] Task: Perform a dry-run and controlled live execution test for the supported API path.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Core Group Follow Sync Execution' (Protocol in workflow.md)
