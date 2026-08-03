# Specification

## Overview

Harden Bluesky archive mirroring based on the ACC recovery incident. Preserve strict separation between archival capture and publication while making source selection, idempotency, reconciliation, state updates, recovery, credentials, and cleanup deterministic.

## Requirements

- Reject records that are not explicitly eligible by source ID, platform, canonical URL, visibility, and content type.
- Treat post creation and public reconciliation as separate durable states.
- Prevent retries from creating duplicates even when public indexing is delayed.
- Scope manual workflow dispatch and state writes to one mirror.
- Provide evidence-backed automated recovery without hand-editing runtime JSON.
- Use public mirror names separately from canonical agency identities.
- Require app passwords for automation and prohibit primary passwords in repository or persistent process environments.
- Produce a reconciliation report for duplicates, excluded-source posts, missing audit entries, and cleanup candidates.

## Acceptance Criteria

- Every child track passes its tests and Conductor review.
- ACC can run repeatedly without YouTube leakage, duplicate LinkedIn publication, or false pauses.
- Profile snapshots cannot be treated as social posts.
- Runtime updates do not conflict across account jobs.
- All external cleanup remains separately authorized and auditable.

## Out of Scope

- Creating additional mirror accounts.
- Mirroring Facebook, Instagram, X, or Threads content.
- Bypassing platform authentication, moderation, or anti-abuse controls.
