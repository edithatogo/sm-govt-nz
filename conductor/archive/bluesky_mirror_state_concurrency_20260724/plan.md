# Plan
- [x] Task: Write migration and concurrent-update tests.
- [x] Task: Define per-account state and append-only audit schemas.
- [x] Task: Implement monolithic-state migration.
- [x] Task: Update workflows and commit helper paths.
- [x] Task: Rebuild aggregate health reports deterministically.
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md).

## Verification evidence

- `uv run --with pytest pytest tests/test_bluesky_mirror_programme.py
  tests/test_bluesky_mirror_programme_workflows.py -q -s`: 28 passed.
- `uvx --offline ruff check src/bluesky_mirror_programme.py
  scripts/manage_bluesky_mirror_programme.py
  tests/test_bluesky_mirror_programme.py
  tests/test_bluesky_mirror_programme_workflows.py`: passed.
