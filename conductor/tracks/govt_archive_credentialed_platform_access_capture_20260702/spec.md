# Specification: NZ Government Archive - credentialed platform access and API capture backlog

## Overview
This track records and hardens the boundary for capture paths that cannot run from public unauthenticated resources alone. It covers optional API gates, readiness reports, secret validation, and auto-transition behaviour when credentials or exports are deliberately supplied.

## Functional Requirements
- Maintain explicit opt-in gates for Threads live API, X API, LinkedIn API/export, Meta platform APIs, and other credentialed captures.
- Ensure disabled credentialed paths produce report-only unavailable states, not failing workflows.
- Ensure enabled credentialed paths fail loudly and issue-worthily on permission, configuration, or quota errors.
- Document required secrets, permissions, expected costs/quotas, and legal/operator prerequisites for each platform.
- Keep manual seed/export paths as the default compliant capture route where official APIs are unavailable or impractical.

## Non-Functional Requirements
- Prefer public, lawful, keyless capture paths unless the track explicitly documents an opt-in credentialed path.
- Preserve existing monthly external publication guards for Hugging Face and Zenodo.
- Keep machine-readable reports deterministic so automation can act without manual decisions.
- Avoid deleting source registrations solely because a source is blocked, missing input, or temporarily unavailable.

## Acceptance Criteria
- Each credentialed source group has a readiness state and documented activation gate.
- Workflows do not attempt live credentialed capture unless the explicit gate and required secrets are present.
- Permission/configuration errors are actionable only when a gated capture path is enabled.
- Future credential availability automatically transitions source status without code changes.
- Docs avoid describing registered-but-unseeded accounts as archived.

## Out of Scope
- Applying for platform approvals or paying for APIs.
- Extracting browser cookies or hidden session state.
- Bypassing platform access controls.

