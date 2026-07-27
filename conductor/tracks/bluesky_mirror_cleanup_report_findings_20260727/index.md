# Bluesky Mirror Cleanup Report Findings

- [Specification](./spec.md)
- [Plan](./plan.md)

Hosted cleanup run `30237376115` found genuine reconciliation discrepancies but
did not commit its reports because the verifier used the same nonzero exit for
findings and execution faults. This track preserves strict CLI validation while
making the scheduled workflow evidence-first and non-destructive.
