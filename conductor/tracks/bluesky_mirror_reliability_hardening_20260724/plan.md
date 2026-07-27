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
- [x] Task: Complete `bluesky_mirror_credential_hygiene_20260724`;
  operator-confirmed rotation and revocation were recorded on 2026-07-27.
- [x] Task: Implement `bluesky_mirror_cleanup_verification_20260724`.
- [x] Task: Complete `bluesky_mirror_cleanup_report_findings_20260727`;
  PR #43 and hosted run 30239062374 preserved both reports.
- [x] Task: Implement and archive `bluesky_mirror_handle_lifecycle_20260724`, GitHub #37.
- [ ] Task: Apply the five exact-URI ACC cleanup candidates and regenerate a
  valid reconciliation report.
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
- Cleanup run 30239062374 preserved ACC and Courts reconciliation reports; ACC
  remains invalid with five exact-URI deletion candidates and no destructive
  action performed.
- Hosted preflight run 30238209314 validated the configured ACC app password,
  expected handle, DID, and dry-run publication without posting.
- On 2026-07-27, the operator confirmed primary-password rotation, isolated
  Environment app-password replacement, and superseded app-password revocation;
  no secret values are retained.
- Issue updates, pushes, and any live posting remain separate approval gates.
