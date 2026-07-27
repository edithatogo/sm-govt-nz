# Review Report: Bluesky Mirror Reliability Hardening

## Summary

The reliability implementation and local credential controls are sound, but the
track remains externally gated by both three still-visible ACC cleanup records
and unverified credential rotation, replacement, and revocation.

## Verification Checks

- [x] **Plan Compliance**: Partial - implementation is complete; destructive
  cleanup and operator credential actions remain outstanding.
- [x] **Style Compliance**: Pass.
- [x] **New Tests**: Yes.
- [x] **Test Coverage**: Yes for hosted status, recovery, credentials, source
  contracts, and cleanup-state classification.
- [x] **Test Results**: Passed - 58 targeted tests, Ruff, Actionlint, and diff
  checks passed on 2026-07-27.

## Findings

### High: Successful cleanup workflow was treated as clean reconciliation

- **File**: `scripts/build_bluesky_mirror_hosted_plan.py`
- **Context**: Run `30239062374` succeeded operationally but recorded
  `findings_valid=false`. Treating workflow success alone as completion hid five
  exact-URI ACC deletion candidates.
- **Resolution**: Fixed locally. Cleanup now completes only when the workflow
  succeeds and `findings_valid=true`; invalid findings produce
  `external_action_required`.

## Remaining External Gate

- GitHub's nonsecret Environment metadata reports `BLUESKY_APP_PASSWORD` was
  last updated at `2026-07-22T11:18:54Z`; this does not verify the claimed
  2026-07-27 replacement or superseded-password revocation.
- Credential completion requires operator-controlled rotation, isolated
  Environment replacement, revocation, and a replacement-credential preflight.
- The ACC cleanup report identified five candidate URIs across three duplicate
  groups and four excluded-source findings.
- The guarded dry-run receipt found two candidates already absent and these
  three candidates still publicly visible:
  - `at://did:plc:vxltrdhni2dfsm4actryhj4n/app.bsky.feed.post/3mrbn6rnwin2s`
  - `at://did:plc:vxltrdhni2dfsm4actryhj4n/app.bsky.feed.post/3mrbq4xt3bx2u`
  - `at://did:plc:vxltrdhni2dfsm4actryhj4n/app.bsky.feed.post/3mrbqcvym3w2a`
- The receipt records `status=dry_run`, `apply_requested=false`, no successful
  delete requests, and no credential material.
- Deleting the three visible records requires separate exact-URI approval,
  followed by public read-back and a regenerated reconciliation report with
  `valid=true`.
- Issue #36 remains open. No issue update, deletion, workflow dispatch, or
  Bluesky posting is authorized by this review.
