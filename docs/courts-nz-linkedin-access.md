# Courts of New Zealand LinkedIn Access Contract

## Decision
The LinkedIn archive adapter should treat official API access as the preferred
method, but it must start in `auth_required` until the operator can provide an
approved LinkedIn developer app and organization-access token.

## Rationale
LinkedIn does not expose the Courts of New Zealand company posts as a stable
first-party RSS feed. The official API route is the LinkedIn Community
Management / Posts API. Microsoft Learn states that retrieving organization
posts requires `r_organization_social`, and the API flow validates organization
access through the authenticated member.

## Approved Access Order
1. Use the LinkedIn Community Management / Posts API if an approved app and
   organization-authorized OAuth token are available.
2. Use a user-authorized browser capture only for bounded archival backfills
   when the operator is logged in and explicitly approves that capture.
3. Use a manually exported seed file if browser capture is unsuitable.
4. Mark the source `auth_required` or `unavailable` rather than scraping
   aggressively.

## Guardrails
- LinkedIn records are archive-only inputs in this track.
- LinkedIn records must not advance Bluesky-to-X syndication state.
- Browser capture must be bounded, operator-authorized, and produce a
  provenance report.
- Raw records should be stored under
  `historical_archive_raw/linkedin/<yyyy-mm>/`.
- Normalized records should be appended under
  `historical_archive_normalized/linkedin/<yyyy-mm>.jsonl`.

## References
- LinkedIn Community Management API product page:
  https://developer.linkedin.com/product-catalog/marketing/community-management-api
- LinkedIn Community Management overview:
  https://learn.microsoft.com/en-us/linkedin/marketing/community-management/community-management-overview
- LinkedIn Posts API:
  https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api
