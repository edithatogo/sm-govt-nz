# Draft GitHub Issue Hierarchy

These payloads are drafts. Publishing them requires separate approval for `edithatogo/sm-govt-nz`.

## Parent subissue of #19

Title: `Bluesky mirror reliability hardening`

Body:

> Harden source eligibility, content contracts, reconciliation, idempotency, workflow isolation, state concurrency, recovery, credentials, and cleanup after the ACC mirror incident. Conductor: `bluesky_mirror_reliability_hardening_20260724`.

## Native subissues of the new parent

1. `Fail closed on Bluesky mirror source eligibility`
   Conductor: `bluesky_mirror_source_eligibility_20260724`
2. `Separate mirrorable posts from profile metadata`
   Conductor: `bluesky_mirror_content_contracts_20260724`
3. `Make Bluesky reconciliation idempotent under delayed indexing`
   Conductor: `bluesky_mirror_reconciliation_idempotency_20260724`
4. `Add mirror-scoped manual workflow dispatch`
   Conductor: `bluesky_mirror_workflow_isolation_20260724`
5. `Partition Bluesky mirror runtime state by account`
   Conductor: `bluesky_mirror_state_concurrency_20260724`
6. `Automate evidence-backed mirror recovery`
   Conductor: `bluesky_mirror_recovery_automation_20260724`
7. `Enforce Bluesky app-password credential hygiene`
   Conductor: `bluesky_mirror_credential_hygiene_20260724`
8. `Reconcile and clean duplicate or excluded mirror posts`
   Conductor: `bluesky_mirror_cleanup_verification_20260724`
9. `Make Bluesky mirror handles DID-safe and migration-aware`
   Conductor: `bluesky_mirror_handle_lifecycle_20260724`
