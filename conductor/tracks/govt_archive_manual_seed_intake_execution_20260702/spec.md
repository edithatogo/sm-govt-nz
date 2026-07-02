# Specification: NZ Government Archive - manual seed intake execution for Threads LinkedIn and newsletters

## Overview
This track turns the existing manual-seed architecture into an executable intake lane for Threads, LinkedIn, and newsletter/email sources. It does not require new scraping architecture; it documents file shapes, sample fixtures, validation, and automated ingestion once lawful seed files are placed in the repository.

## Functional Requirements
- Define and validate seed file schemas for Threads, LinkedIn, and newsletter/email inputs.
- Provide example seed fixtures that are safe, synthetic, and representative of the expected operator-provided payloads.
- Ensure missing seeds remain report-only states and do not create implementation-blocker issues.
- Ensure present valid seeds archive automatically into canonical raw and normalized paths.
- Generate operator-facing status reports that distinguish missing, invalid, empty, and archived seed states.

## Non-Functional Requirements
- Prefer public, lawful, keyless capture paths unless the track explicitly documents an opt-in credentialed path.
- Preserve existing monthly external publication guards for Hugging Face and Zenodo.
- Keep machine-readable reports deterministic so automation can act without manual decisions.
- Avoid deleting source registrations solely because a source is blocked, missing input, or temporarily unavailable.

## Acceptance Criteria
- Threads, LinkedIn, and newsletter seed paths have documented accepted formats and validation behaviour.
- Synthetic sample fixtures are covered by tests without introducing real private data.
- Valid seed inputs are archived through existing workflows without manual code changes.
- Invalid or empty seeds raise actionable issue/report states, while missing seeds remain tracked coverage gaps.
- Reports clearly describe which accounts are registered, monitored, and actually archived.

## Out of Scope
- Obtaining or creating real seed exports from external platforms.
- Logged-in browser capture.
- Changing platform terms or requiring API approvals.

