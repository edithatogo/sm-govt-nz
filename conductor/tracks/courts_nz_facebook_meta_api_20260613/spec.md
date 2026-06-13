# Specification - Courts of New Zealand Facebook Page Meta API Mirror

## Overview
After Threads is set up, add a separate Facebook Page mirror lane for Courts of
New Zealand content using official Meta Pages APIs. This track may use the same
Meta account/admin ownership as Threads where practical, but posts must be made
as the mirror Page, not a personal Facebook profile.

## Requirements
1. Account identity:
   - Use a dedicated Facebook Page identity aligned with `Mirror: Courts of New
     Zealand`.
   - Do not post under Dylan Mordaunt, `edithatogo`, or any personal Facebook
     profile.
   - Use the same Meta account/admin structure as Threads only for ownership and
     administration.
2. API route:
   - Use official Meta Pages API publishing endpoints.
   - Store Facebook Page ID, page access token, app ID, and app permissions
     separately from Threads and Instagram.
3. Posting contract:
   - Preserve source text and attribution without commentary.
   - Use separate duplicate-prevention state.
   - Start with new forward posts only; historical replay requires a separate
     review because Facebook Page posts would appear as current posts.

## Acceptance Criteria
- A non-posting credential probe validates Page identity and posting permission
  shape.
- Secret schema and validation workflow list Facebook-specific secrets.
- A dry-run payload builder handles text, attribution, and first-image Page
  publishing constraints.
- A controlled live post is possible only after explicit config enablement and
  review.
