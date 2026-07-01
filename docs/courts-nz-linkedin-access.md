# Courts of New Zealand LinkedIn Access Contract

## Decision
The LinkedIn archive adapter should treat official API access as the preferred
method, but it must start in `auth_required` until the operator can provide an
approved LinkedIn developer app and organization-access token.

LinkedIn is source-only for the current roadmap. Do not implement or run
LinkedIn posting from this repository, and do not post through a personal
LinkedIn profile. Any future LinkedIn outbound work requires a separate
conductor track, explicit risk review, and a dedicated mirror/organization
identity.

Any LinkedIn developer app or OAuth work performed during exploratory setup is
not approved as an outbound posting route. If LinkedIn posting is reopened, the
account/app setup must be recreated or reviewed under the agreed non-personal
mirror structure, with administration under `edithatogo@gmail.com` where
practical and no posting authority for Dylan Mordaunt or `edithatogo` personal
profiles.

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

## Manual Seed Import
Use `scripts/archive_linkedin_seed.py` when an operator-authorized LinkedIn
export or bounded browser capture has been reviewed and saved as JSON.

Accepted seed shape:

```json
{
  "posts": [
    {
      "post_id": "urn:li:activity:123",
      "url": "https://www.linkedin.com/feed/update/urn:li:activity:123/",
      "created_at": "2026-06-10T00:00:00Z",
      "text": "Post text",
      "media": [
        {
          "url": "https://example.test/image.jpg",
          "media_type": "image",
          "alt_text": ""
        }
      ]
    }
  ]
}
```

Run:

```powershell
uv run --python 3.14 python scripts/archive_linkedin_seed.py --seed-json imports/linkedin/courts-nz-linkedin-seed.json --report conductor/linkedin_archive_report.json
```

The script writes raw source evidence under
`historical_archive_raw/linkedin/<yyyy-mm>/`, appends normalized records under
`historical_archive_normalized/linkedin/<yyyy-mm>.jsonl`, and writes a
provenance/access report. The script is idempotent by LinkedIn post ID or a
stable URL/date/text hash when no post ID is available.

Obtaining the approved source export is tracked in
https://github.com/edithatogo/sm-govt-nz/issues/7.

## Guardrails
- LinkedIn records are archive-only inputs in this track.
- LinkedIn records must not advance Bluesky-to-X syndication state.
- LinkedIn must not be used as an outbound posting target in the current MVP.
- Do not create or use tokens that post as Dylan Mordaunt, `edithatogo`, or any
  personal identity.
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
