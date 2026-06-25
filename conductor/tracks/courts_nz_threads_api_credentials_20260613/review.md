# Review - Courts of New Zealand Threads API Credentials

**Track ID:** `courts_nz_threads_api_credentials_20260613`
**Review Date:** 2026-06-25
**Reviewer:** Conductor Track Reviewer Agent

## Summary
All 9 tasks across 3 phases are fully implemented and verified. Threads API credential contracts, secret schema, and non-posting validation are complete. Live posting remains gated by adapter launch review. No fixes required.

## Plan Compliance
All 9 tasks across 3 phases are marked `[x]`:

| Phase | Task | Status | Evidence |
|-------|------|--------|----------|
| Phase 1: Contract Research | Confirm Threads API fields, scopes, profile IDs, token lifetime | ✅ | Meta documentation referenced |
| Phase 1: Contract Research | Decide Buffer fallback status | ✅ | Buffer removed from launch path |
| Phase 1: Contract Research | Document free-tier/quota implications | ✅ | Documented |
| Phase 2: Secret Schema | Add Threads secret names to `config/secrets.schema.json` | ✅ | `THREADS_ACCESS_TOKEN`, `THREADS_USER_ID` |
| Phase 2: Secret Schema | Extend `scripts/validate_secrets.py` for `--target threads` | ✅ | Threads validation implemented |
| Phase 2: Secret Schema | Unit tests for missing, partial, valid Threads secret sets | ✅ | `test_validate_secrets.py` |
| Phase 3: Non-Posting Probe | Implement Threads credential probe (read-only) | ✅ | `scripts/threads_api_probe.py` |
| Phase 3: Non-Posting Probe | GitHub Actions wiring for probe | ✅ | `.github/workflows/validate_threads.yml` |
| Phase 3: Non-Posting Probe | Document credential rotation/revocation | ✅ | Setup docs updated |

## Completion Evidence
- ✅ Meta app `Courts NZ Mirror` has `mirnzcourts` accepted as Threads tester
- ✅ GitHub Actions secrets `THREADS_ACCESS_TOKEN` and `THREADS_USER_ID` configured for `edithatogo/sm-govt-nz`
- ✅ Manual `Validate Threads` workflow run `27458588485` passed
- ✅ Live Threads syndication remains disabled in `config.json` (gated by adapter launch review)

## Spec Compliance
- ✅ Prefer official Threads API route for `https://www.threads.com/@mirnzcourts`
- ✅ Documented Meta app, Threads user/profile ID, access token scope, token refresh/expiry
- ✅ GitHub secret names and validation logic without storing tokens in Git
- ✅ Validation does not create, publish, or delete Threads posts
- ✅ Threads disabled in `config.json` until adapter launch review passes

## Acceptance Criteria
- ✅ `config/secrets.schema.json` includes Threads secret contract
- ✅ `scripts/validate_secrets.py --mode syndicate --target threads` verifies environment shape
- ✅ Probe command (`scripts/threads_api_probe.py`) verifies credentials without publishing
- ✅ Docs explain credential rotation/revocation

## Code Quality
- Ruff: ✅ All checks passed (`ruff check --no-cache src tests scripts`)
- pytest: ✅ Secret validation tests pass

## Archive Decision
**ARCHIVED** — All deliverables complete and verified. Threads credentials ready for adapter launch.