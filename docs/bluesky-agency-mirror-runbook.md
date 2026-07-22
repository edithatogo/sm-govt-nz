# Bluesky Agency Archive Mirror Runbook

## Boundary

Archival is read-only. Only workflows named `Bluesky Mirror ...` may publish, and only to project-controlled, explicitly unofficial archive accounts. Account creation is local, operator-supervised, and limited to one account per day.

## Onboarding

1. Take the next candidate from `config/mirror_accounts.json` in deterministic order.
2. Open its GitHub onboarding subissue and account packet.
3. Construct `edithatogo+bluesky-<agency-id>@gmail.com` in local operator memory; never commit it.
4. Use the local onboarding agent with SeleniumBase UC and Playwright CDP.
5. Stop before final registration submission, CAPTCHA, or platform challenge.
6. After operator submission, search the exact alias mailbox through the designated administrative account:
   `gog --account edithatogo@gmail.com gmail search 'to:edithatogo+bluesky-<agency-id>@gmail.com'`.
   Complete verification only for the matching agency alias; never use another account implicitly.
7. Apply archive branding, unofficial disclosure, official-source links, and the Bluesky bot label.
8. Store the primary password in Windows Credential Manager.
9. Create GitHub Environment `bluesky-mirror-<agency-id>` and set `BLUESKY_HANDLE` and `BLUESKY_APP_PASSWORD` without logging values.
10. Run `Bluesky Mirror Preflight`. Keep `enabled=false` until it passes.

## Launch

Set the account to `backfilling`, add `activated_at`, and enable it only after preflight. Set repository variable `BLUESKY_MIRRORING_ENABLED=true` only when at least one account is approved for posting. The historical workflow posts once every six hours, while ongoing records are checked every 15 minutes.

Every post must be attributable, idempotent, and publicly reconciled. Deleted, withdrawn, private, session-only, and unverifiable records remain excluded from mirroring even when retained lawfully in the archive.

## Incident response

Dispatch `Bluesky Mirror Emergency Pause` for one mirror or `all`. Authentication, moderation, deletion, duplicate, mismatch, and public-readback anomalies fail closed. Do not delete posts automatically and do not interrupt archival capture or monthly Hugging Face/Zenodo publication.

## Follow topology

No workflow performs live follows. During supervised onboarding, an agency mirror may follow the clearly labeled corpus index once, and the index may follow it once. Likes, replies, quotes, reposts, direct messages, and full-mesh following are out of scope.
