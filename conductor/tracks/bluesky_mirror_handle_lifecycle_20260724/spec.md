# Specification

## Overview

Make Bluesky mirror handles deterministic, jurisdiction-aware, and safely migratable while treating the account DID as permanent identity.

## Requirements

- Maintain a canonical organisation-abbreviation registry.
- Use `<organisation-abbreviation>-<country-or-jurisdiction>-arc.bsky.social`.
- Use stable numbered suffixes for collisions.
- Pin created accounts to immutable DIDs.
- Record append-only handle history.
- Reserve retired handles so they cannot be reassigned to another mirror.
- Produce migration plans and public DID verification.
- Detect stale references without scanning archive payloads.
- Recheck availability immediately before migration and verify the DID immediately afterwards.
- Monitor retired handles for unexpected re-registration or misleading impersonation.
- Require explicit, evidenced approval for every organisation abbreviation.
- Keep custom-domain migration disabled until domain-control evidence and operator approval exist.
- Update GitHub Environment handles and pass non-posting preflight before completion.
- Keep primary passwords out of persistent environment variables.

## Acceptance Criteria

- `acc-nz-arc.bsky.social` resolves to the recorded ACC DID.
- CI rejects malformed handles, duplicate abbreviations, duplicate handles, and invalid DIDs.
- Migration plans contain no credentials.
- Stale-link reports are bounded and machine-readable.
- Retired-handle monitoring distinguishes unregistered handles, retained aliases, unexpected registrations, and monitoring faults.
- Custom-domain plans are non-operative and cannot authorize automatic migration.
- The ACC GitHub Environment passes preflight with the new handle.

## Out of Scope

- Automated account registration.
- Automatic destructive rollback or handle reassignment.
- Secret extraction or primary-password rotation without operator authorization.
