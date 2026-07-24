# Review Report: Bluesky Mirror Handle Lifecycle

## Summary

The implementation satisfies the local identity-governance contract after
fail-closed HTTP classification and migration-availability fixes.

## Verification Checks

- **Plan Compliance**: Partial - repository work is complete; password rotation
  and GitHub issue publication remain separately governed external actions.
- **Style Compliance**: Pass.
- **New Tests**: Yes.
- **Test Coverage**: Yes - registry, DID, migration, stale-link, retired-handle,
  custom-domain, and malformed HTTP response behavior are covered.
- **Test Results**: Passed locally and in hosted CI.

## Findings Resolved

### High: Generic HTTP 400 was treated as handle availability

Only an explicit public resolver response stating that a handle cannot be
resolved now counts as `unregistered`. Other errors become actionable
`monitoring_fault` evidence.

### Medium: Availability checks could not fail closed

The CLI now supports `availability --require-unregistered`, which exits
unsuccessfully for registered handles and inconclusive probes.

## External Gates

- Rotate the ACC primary password through an operator-controlled Bluesky
  session.
- Publish and cross-reference the reviewed GitHub subissue payload.
