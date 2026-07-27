# Specification

Treat an empty Bluesky mirror workflow matrix as an expected successful no-op.
Matrix generation must preserve the true empty selection for reporting, provide a
non-runnable sentinel matrix for GitHub expression validation, and expose an
explicit `has_targets` output. Posting jobs must never evaluate credentials or
posting code when no target is eligible.

## Acceptance

- Ongoing and historical workflows finish successfully when no mirrors are eligible.
- Run summaries display the true empty matrix.
- Posting jobs, environments, credentials, and AT Protocol writes are skipped.
- Non-empty matrices retain existing account isolation and posting behavior.
- Hosted dry-run evidence confirms the no-op path.
