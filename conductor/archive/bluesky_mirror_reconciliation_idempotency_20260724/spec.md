# Specification

Reserve deterministic idempotency keys before posting. Persist `planned`, `submitted`, `pending_reconciliation`, `reconciled`, and `failed` states with URI/CID evidence. Retry public read-back asynchronously and search by known URI/hash before any replacement post. Delayed indexing must not cause duplicate publication.

Acceptance requires repeated retries to create at most one Bluesky record and transient read-back failures not to pause an account prematurely.
