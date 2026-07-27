# Specification

The scheduled Bluesky cleanup verifier must preserve reconciliation findings as
durable, non-destructive reports. Expected findings such as deleted public posts
or public posts missing from the repository audit must not prevent the report
commit step from running.

Strict verification remains the default for direct CLI use and tests. Only an
explicit report-only option may convert a findings result into a successful
process exit. The workflow remains read-only with respect to Bluesky and must not
receive write credentials or delete posts.

## Acceptance

- The CLI exits nonzero for findings unless `--report-only` is explicit.
- The cleanup workflow uses report-only mode and commits per-mirror reports.
- Reports retain `valid: false` and all findings without masking them.
- No Bluesky credential, post, or delete capability is introduced.
- A hosted workflow run commits reports for both enabled mirrors.
