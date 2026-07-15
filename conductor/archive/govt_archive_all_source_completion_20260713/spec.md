# Specification - Complete Archival Coverage for All Identified Government Sources

## Overview

Create the canonical completion system for all 5,602 government archive readiness candidates. Every source must retain a stable identity and progress to archived evidence or an evidence-backed terminal state.

## Functional Requirements

- Generate one completion row for every readiness candidate and reconcile exactly to the readiness total.
- Overlay registration, archive report, normalized record and external publication evidence without mutating source registries.
- Distinguish discovery, registration, scheduling, capture, archive success, terminal evidence and automation faults.
- Never count workflow setup, `seed_present`, or public-fallback availability as archived content.
- Generate a deterministic, bounded work queue with exact workflow inputs and acceptance conditions.
- Reopen external-access rows automatically when lawful seeds or approved capture paths appear.
- Run daily in GitHub Actions and retain monthly guarded Hugging Face/Zenodo publication.

## Non-Functional Requirements

- Python 3.14 only; deterministic JSON and Markdown outputs.
- No login automation, CAPTCHA solving, credential extraction, private API calls or TLS verification bypass.
- Expected empty, deleted, invalid and externally gated states are report-only; issues are reserved for automation faults.

## Acceptance Criteria

- The matrix contains exactly 5,602 unique source IDs.
- Every row has evidence, next action and acceptance fields.
- Archived rows have archive and publication evidence.
- All incomplete rows appear in deterministic priority order in the work queue.
- Completion cannot be claimed while any row lacks archived or terminal evidence.
