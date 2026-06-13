# Plan - Courts of New Zealand Threads API Credentials

## Phase 1: Contract Research
- [ ] Task: Confirm official Threads API fields, scopes, profile IDs, and token
  lifetime requirements from Meta documentation.
- [ ] Task: Decide whether Buffer remains a fallback or is removed from the
  launch path.
- [ ] Task: Document free-tier or quota implications.

## Phase 2: Secret Schema
- [ ] Task: Add Threads secret names to `config/secrets.schema.json`.
- [ ] Task: Extend `scripts/validate_secrets.py` for `--target threads`.
- [ ] Task: Add unit tests for missing, partial, and valid Threads secret sets.

## Phase 3: Non-Posting Probe
- [ ] Task: Implement a Threads credential probe that reads account/profile
  identity only.
- [ ] Task: Add GitHub Actions wiring for the probe behind a disabled or manual
  gate.
- [ ] Task: Document setup and rotation in `SETUP_GUIDE.md`.
