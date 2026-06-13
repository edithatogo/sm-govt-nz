# Specification - Courts of New Zealand Instagram Meta API Mirror

## Overview
After Threads is set up, add a separate Instagram mirror lane for Courts of New
Zealand content using official Meta Instagram APIs. This track may use the same
Meta account/admin ownership as Threads where practical, but it must not share
posting state or assume Threads tokens authorize Instagram publishing.

## Requirements
1. Account identity:
   - Use a dedicated mirror identity aligned with `Mirror: Courts of New
     Zealand`.
   - Do not post under Dylan Mordaunt, `edithatogo`, or any personal Instagram
     identity.
   - Use the same Meta account/admin structure as Threads only for ownership and
     administration, not as a posting identity.
2. API route:
   - Use official Meta Instagram APIs for content publishing.
   - Confirm whether the mirror account must be a professional, business, or
     creator account before implementation.
   - Store Instagram profile/account IDs and tokens separately from Threads.
3. Posting contract:
   - Preserve source text and attribution without commentary.
   - Use separate duplicate-prevention state.
   - Start with new forward posts only; historical replay requires a separate
     review because Instagram posts cannot be treated as backdated corpus
     imports by default.

## Acceptance Criteria
- A non-posting credential probe validates the Instagram account/profile
  identity.
- Secret schema and setup docs list Instagram-specific secrets.
- A dry-run payload builder handles text, links, and media constraints.
- A controlled live post is possible only after explicit config enablement and
  review.
