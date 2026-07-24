# Plan
- [x] Task: Write delayed-indexing and retry race tests.
- [x] Task: Define durable publication state transitions.
- [x] Task: Reserve idempotency records before network submission.
- [x] Task: Implement asynchronous reconciliation and bounded escalation.
- [x] Task: Prove retry and crash recovery do not duplicate posts.
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md).

## Implementation evidence

- Publication state is persisted as `planned`, `submitted`,
  `pending_reconciliation`, `reconciled`, or `failed`.
- A deterministic key binds mirror, source, archive record, and rendered content
  before any network submission.
- Existing reservations are reconciled without issuing another create request.
- Read-back misses remain pending and only pause after 12 unresolved checks.
- Added regression coverage for delayed indexing and ambiguous submission
  timeouts.
- `uv run --with pytest pytest tests/test_bluesky_mirror_programme.py
  tests/test_bluesky_mirror_programme_workflows.py -q -s`: 23 passed.
- `uvx ruff check src/bluesky_mirror_programme.py
  tests/test_bluesky_mirror_programme.py`: passed.
- Conductor review found and fixed the backfill-cap audit regression; the
  verification commands passed again after the fix.
