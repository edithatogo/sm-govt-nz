# Specification: NZ Government Archive - website and YouTube fixable failure remediation

## Overview
This track remediates the archive gaps that can be addressed with the current repository, manifests, and public unauthenticated access. It focuses on website failure classes and YouTube URL/channel resolver failures surfaced by the archive gap map, without adding new platform credentials or changing the monthly publication guard.

## Functional Requirements
- Classify residual website failures by fixability, including DNS failures, method failures, timeout, not found, not acceptable, and persistent capture blocks.
- Improve website URL canonicalization, protocol and hostname fallback, and GET fallback behaviour where existing probes are too strict.
- Improve YouTube source normalization for malformed handles, duplicate URLs, channel IDs, and empty/no-record outcomes.
- Regenerate failure triage and archive gap reports so fixed, retired, blocked, and no-record states are machine-readable.
- Keep false-positive remediation safe by preserving source evidence and marking uncertain cases for review rather than deleting them.

## Non-Functional Requirements
- Prefer public, lawful, keyless capture paths unless the track explicitly documents an opt-in credentialed path.
- Preserve existing monthly external publication guards for Hugging Face and Zenodo.
- Keep machine-readable reports deterministic so automation can act without manual decisions.
- Avoid deleting source registrations solely because a source is blocked, missing input, or temporarily unavailable.

## Acceptance Criteria
- Website and YouTube failure classes are represented in updated reports with actionable/non-actionable separation.
- Fixable URL and resolver failures are retried through workflows without requiring new credentials.
- Persistent blocked or retired sources remain tracked as explicit status states rather than generic failures.
- Targeted tests cover canonicalization and report classification changes.
- Relevant scheduled workflows continue to publish artifacts and respect monthly external-release guards.

## Out of Scope
- Credentialed website capture, CAPTCHA handling, login flows, or bypass techniques.
- Official YouTube Data API integration that requires keys.
- Manual operator review of every source.

