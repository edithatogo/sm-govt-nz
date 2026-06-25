# Spec - NZ Government Archive - explicit credentialed platform onboarding backlog

## Problem
Meta, LinkedIn, X, and similar platforms may require account creation, app approval, paid access, or manual administration. The repo should record these as explicit onboarding work rather than pretending they are live-capturable.

## Scope
Define platform boundaries, manual seed records, credential requirements, official API paths, validation commands, and future automation gates.

## Required Outputs
- Per-platform onboarding checklist.
- `blocked_credential` readiness state for account/API-gated platforms.
- Secret names, permission scopes, rate-limit notes, and validation probes.

## Acceptance Criteria
- Credentialed platforms are visible without blocking non-credential capture.
- Every user-required action is explicit and tied to a validation command.
- Future mirroring keeps personal identities out of posting.
