# Plan

## Phase 1: Contracts and source boundaries
- [x] Task: Implement `bluesky_mirror_source_eligibility_20260724`.
- [x] Task: Implement `bluesky_mirror_content_contracts_20260724`.
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md).

## Phase 2: Publication reliability
- [x] Task: Implement `bluesky_mirror_reconciliation_idempotency_20260724`.
- [x] Task: Implement `bluesky_mirror_workflow_isolation_20260724`.
- [x] Task: Implement `bluesky_mirror_state_concurrency_20260724`.
- [x] Task: Complete `bluesky_mirror_empty_matrix_noop_20260727`; hosted run 30236905723 proved the successful no-op path.
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md).

## Phase 3: Operations and security
- [x] Task: Implement `bluesky_mirror_recovery_automation_20260724`.
- [ ] Task: Complete `bluesky_mirror_credential_hygiene_20260724`;
  Environment replacement and revocation remain externally unverified.
- [x] Task: Implement `bluesky_mirror_cleanup_verification_20260724`.
- [x] Task: Complete `bluesky_mirror_cleanup_report_findings_20260727`;
  PR #43 and hosted run 30239062374 preserved both reports.
- [x] Task: Implement and archive `bluesky_mirror_handle_lifecycle_20260724`, GitHub #37.
- [x] Task: Delete the three still-visible ACC cleanup URIs and regenerate a
  valid reconciliation report; apply run 30251127441 and verification run
  30252454725 completed without remaining candidates.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md).

## Phase 4: Programme closeout
- [x] Task: Run Conductor review for every child track.
- [ ] Task: Reconcile GitHub issue/subissue evidence.
- [x] Task: Archive completed child tracks and update parent programme evidence.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md).

## Reconciliation snapshot

- Completed and archived: source eligibility, content contracts,
  reconciliation/idempotency, state concurrency, recovery automation, cleanup,
  handle lifecycle, and empty-matrix no-op.
- Hosted run 30236905723 proved the empty-matrix successful no-op behavior.
- Cleanup apply run 30251127441 deleted three approved ACC records and confirmed
  two approved records were already absent. It recorded no credential material.
- Verification run 30252454725 committed valid ACC and Courts reports. ACC now
  records five approved tombstones, zero still-visible approved deletions, zero
  unexplained missing records, and zero cleanup candidates.
- The seven-day post-remediation observation window runs through 2026-08-03.
- Hosted preflight run 30238209314 validated the configured ACC app password,
  expected handle, DID, and dry-run publication without posting.
- GitHub Environment metadata still dates `BLUESKY_APP_PASSWORD` to
  `2026-07-22T11:18:54Z`; primary-password rotation, Environment replacement,
  and superseded app-password revocation remain unverified.
- Issue updates, pushes, and any live posting remain separate approval gates.
