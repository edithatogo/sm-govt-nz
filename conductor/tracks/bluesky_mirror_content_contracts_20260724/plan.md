# Plan
- [x] Task: Write content-type and public-name contract tests. `abb8667c`
- [x] Task: Add mirrorable content-type schema. `abb8667c`
- [x] Task: Add `public_name` to registry validation and rendering. `abb8667c`
- [x] Task: Reject profile snapshots from posting. `abb8667c`
- [x] Task: Validate excerpts, numbering, provenance, and length limits. `abb8667c`
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md).

## Verification Evidence

- `uv run pytest tests/test_bluesky_mirror_programme.py -q`: 19 passed.
- `uv run ruff check src/bluesky_mirror_programme.py tests/test_bluesky_mirror_programme.py`: passed.
- Production registry validation: 225 mirror rows accepted.
- ACC contract: `public_name=ACC`; handle `acc-nz-arc.bsky.social`.
- Repository-wide pytest collection remains affected by the existing Python 3.14 capture teardown error.

## Phase: Review Fixes

- [x] Task: Apply review suggestions `e0784a18`
