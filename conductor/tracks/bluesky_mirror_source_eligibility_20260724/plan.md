# Plan
- [x] Task: Write eligibility and provenance fixtures.
- [x] Task: Define the fail-closed eligibility result schema.
- [x] Task: Implement source ID, platform, URL, visibility, and agency checks.
- [x] Task: Emit accepted/rejected counts and reasons.
- [x] Task: Run targeted tests and workflow dry-run.
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md).

## Verification Evidence

- `uv run pytest tests/test_bluesky_mirror_programme.py -q`: 16 passed.
- `uv run ruff check scripts/manage_bluesky_mirror_programme.py src/bluesky_mirror_programme.py tests/test_bluesky_mirror_programme.py`: passed.
- GitHub Actions run `30069129687`: successful manual historical-backfill dry-run.
- Hosted checks for commit `dca2e28d84c2fb5f38e2e22a30ba419acb931537`: all required checks passed.
- Local full-suite collection under Python 3.14 hit a pytest capture teardown error; `ty` is not installed in the project environment.
