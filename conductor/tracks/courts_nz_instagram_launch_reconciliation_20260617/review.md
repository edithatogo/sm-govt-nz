# Review - Courts of New Zealand Instagram Launch Reconciliation

**Track ID:** `courts_nz_instagram_launch_reconciliation_20260617`
**Review Date:** 2026-06-25
**Reviewer:** Conductor Track Reviewer Agent

## Summary
All 11 tasks across 4 phases are complete. Reconciliation determined that earlier launch-complete notes were stale — Instagram is correctly deferred in runtime config. No fixes required.

## Plan Compliance
| Phase | Task | Status | Evidence |
|-------|------|--------|----------|
| Phase 1: Runtime Audit | Compare config, delivery state, workflow runs, track notes | ✅ | `conductor/instagram_launch_reconciliation_20260617.json` |
| Phase 1: Runtime Audit | Determine if earlier notes were stale/reverted | ✅ | Found stale launch notes; runtime truth confirms disabled |
| Phase 1: Runtime Audit | Update older Instagram track with reconciliation note | ✅ | `courts_nz_instagram_meta_api_20260613/metadata.json` updated |
| Phase 2: Credential/Identity Check | Run non-posting Instagram probe | ✅ | `scripts/instagram_api_probe.py` — blocked (no credentials) |
| Phase 2: Credential/Identity Check | Confirm profile URL is dedicated mirror account | ✅ | `@mirnzcourts` configured in repo metadata |
| Phase 2: Credential/Identity Check | Confirm no personal Instagram identity used | ✅ | No personal identity configured |
| Phase 3: Relaunch/Defer | Dry-run payload review | ✅ Deferred | Blocked by missing credentials |
| Phase 3: Relaunch/Defer | Enable and run live post | ✅ Deferred | Blocked by missing credentials |
| Phase 3: Relaunch/Defer | If blocked, record blocker | ✅ | Full blocker documented in evidence JSON |
| Phase 4: Closeout | Verify public delivery URL or defer status | ✅ | Deferred status confirmed in config |
| Phase 4: Closeout | Commit config/state/track changes | ✅ | Evidence committed |
| Phase 4: Closeout | Update tracks.md and platform status review | ✅ | Updated in tracks.md and social_platform_track_review.md |

## Spec Compliance
- ✅ `config.json` treated as launch source of truth
- ✅ No personal Instagram identity used
- ✅ Official Meta Instagram APIs only
- ✅ Delivery state kept separate from Bluesky/Threads/Facebook/X
- ✅ Historical replay disabled

## Acceptance Criteria
- ✅ Reason for disabled runtime state is documented
- ✅ Instagram credential probe was attempted (blocked by missing secrets)
- ✅ Outcome: explicitly deferred with blocker recorded
- ✅ Older Instagram track updated to point to reconciliation outcome

## Code Quality
- Ruff: ✅ All checks passed
- pytest: ✅ 12/12 Instagram readiness tests passed

## Key Artifacts
- `conductor/instagram_launch_reconciliation_20260617.json` — Full reconciliation evidence
- `conductor/tracks/courts_nz_instagram_meta_api_20260613/metadata.json` — Updated with deferred_reason
- `config.json` — `instagram.enabled` remains false; `instagram` not in `syndicate_to`

## Archive Decision
**ARCHIVED** — Reconciliation complete. Launch deferred pending Instagram Graph API credentials.