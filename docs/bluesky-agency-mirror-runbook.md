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
8. Store the primary password only in Windows Credential Manager. Do not keep it in persistent environment variables.
9. Create a dedicated Bluesky app password for automation.
10. Create GitHub Environment `bluesky-mirror-<agency-id>` and set `BLUESKY_HANDLE` and `BLUESKY_APP_PASSWORD` without logging values.
11. Run `Bluesky Mirror Preflight`. Keep `enabled=false` until it passes.

## Handle policy and migration

Primary handles use `<organisation-abbreviation>-<country-or-jurisdiction>-arc.bsky.social`. Numbered collisions use `<organisation-abbreviation>-<country-or-jurisdiction>-arc-<number>.bsky.social`.

The canonical abbreviation and immutable account DID are recorded in `config/bluesky_mirror_abbreviations.json`. The DID, not the handle, is the permanent identity.

Before a handle migration:

```powershell
uv run python scripts/manage_bluesky_mirror_handle.py availability --handle <new-handle> --require-unregistered
uv run python scripts/manage_bluesky_mirror_handle.py plan --mirror-id accident-compensation-corporation --old-handle accident-comp-arc.bsky.social
```

The availability command fails closed unless the public resolver specifically
reports that the proposed handle cannot be resolved. A generic HTTP error is not
evidence that a handle is available.

After the account, registry, and GitHub Environment are updated:

```powershell
uv run python scripts/manage_bluesky_mirror_handle.py verify --mirror-id accident-compensation-corporation
uv run python scripts/manage_bluesky_mirror_handle.py stale-links --old-handle accident-comp-arc.bsky.social
```

Append a nonsecret event to `conductor/bluesky_mirror_handle_history.jsonl`. Every event records the old handle, new handle, DID, reason, timestamp, and public verification evidence. A handle migration is incomplete until the non-posting preflight passes.

Organisation abbreviations are never inferred automatically. Add one only after
operator review, record its approval date and evidence, and preserve the old
handle in `retired_handles`.

The daily health workflow checks retired handles through the public identity API.
Any retained alias, unexpected registration, or monitoring failure is actionable;
an unregistered retired handle is healthy.

Custom-domain handles are deferred. Generate a non-operative readiness plan with:

```powershell
uv run python scripts/manage_bluesky_mirror_handle.py custom-domain-plan --agency-id accident-compensation-corporation
```

Migration remains disabled until domain control, DNS or well-known resolution,
public DID resolution, non-posting preflight, and explicit operator approval are
all evidenced.

## Launch

Set the account to `backfilling`, add `activated_at`, and enable it only after preflight. Set repository variable `BLUESKY_MIRRORING_ENABLED=true` only when at least one account is approved for posting. The historical workflow posts once every six hours, while ongoing records are checked every 15 minutes.

Every post must be attributable, idempotent, and publicly reconciled. Deleted, withdrawn, private, session-only, and unverifiable records remain excluded from mirroring even when retained lawfully in the archive.

## Incident response

Dispatch `Bluesky Mirror Emergency Pause` for one mirror or `all`. Authentication, moderation, deletion, duplicate, mismatch, and public-readback anomalies fail closed. Do not delete posts automatically and do not interrupt archival capture or monthly Hugging Face/Zenodo publication.

## Follow topology

No workflow performs live follows. During supervised onboarding, an agency mirror may follow the clearly labeled corpus index once, and the index may follow it once. Likes, replies, quotes, reposts, direct messages, and full-mesh following are out of scope.
