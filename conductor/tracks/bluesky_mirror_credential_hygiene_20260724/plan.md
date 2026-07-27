# Plan
- [x] Task: Write secret-exclusion and credential-mode tests.
- [x] Task: Add app-password-only configuration assertions.
- [x] Task: Add nonsecret credential-health reporting.
- [x] Task: Remove persistent primary-password environment usage.
- [ ] Task: Rotate the ACC primary password when secure operator entry is available.
- [x] Task: Document rotation and incident response.
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md).

## Rotation and incident response

- Automation accepts only per-account Bluesky app passwords with the standard
  four-group format; primary passwords are rejected before login.
- Credential reports record only presence, format, registry match, mode, and
  validity booleans. They never include secret values.
- Rotate a suspected app password in Bluesky, replace only
  `BLUESKY_APP_PASSWORD` in the corresponding GitHub Environment, run the
  non-posting preflight, and revoke the old app password.
- Primary-password rotation and remote Environment replacement remain explicit
  operator actions and are not inferred from local validation.

## Local verification evidence

- Targeted Bluesky, workflow, and secret-validation tests: 57 passed.
- Ruff passed for the changed Python implementation and tests.
- Hosted preflight run `30238209314` passed against the isolated ACC
  environment without posting and verified that the currently configured app
  password authenticates successfully.
- GitHub reports `BLUESKY_APP_PASSWORD` was last updated on 2026-07-22, so
  replacement and revocation of the prior app password remain unverified.
