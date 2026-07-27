# Plan

## Phase 1: Contracts and source boundaries
- [x] Task: Implement `bluesky_mirror_source_eligibility_20260724`.
- [x] Task: Implement `bluesky_mirror_content_contracts_20260724`.
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md).

## Phase 2: Publication reliability
- [x] Task: Implement `bluesky_mirror_reconciliation_idempotency_20260724`.
- [x] Task: Implement `bluesky_mirror_workflow_isolation_20260724`.
- [x] Task: Implement `bluesky_mirror_state_concurrency_20260724`.
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md).

## Phase 3: Operations and security
- [x] Task: Implement `bluesky_mirror_recovery_automation_20260724`.
- [ ] Task: Complete `bluesky_mirror_credential_hygiene_20260724`;
  local controls are verified, operator rotation remains external.
- [x] Task: Implement `bluesky_mirror_cleanup_verification_20260724`.
- [x] Task: Implement and archive `bluesky_mirror_handle_lifecycle_20260724`, GitHub #37.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md).

## Phase 4: Programme closeout
- [x] Task: Run Conductor review for every child track.
- [ ] Task: Reconcile GitHub issue/subissue evidence.
- [x] Task: Archive completed child tracks and update parent programme evidence.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md).

## Reconciliation snapshot

- Completed and archived: source eligibility, content contracts,
  reconciliation/idempotency, state concurrency, recovery automation, cleanup
  verification, and handle lifecycle.
- No local implementation gaps remain.
- External action: rotate ACC primary credentials and replace the isolated
  GitHub Environment app password.
- Hosted dry-runs, issue updates, and pushes remain separate approval gates.
