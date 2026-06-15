# Courts of New Zealand Email Ingress Fallback Decision

## Decision
Cloudflare Email Routing Worker remains the default ingress route for Courts of
New Zealand judgments of public interest subscription messages.

Mailgun inbound parse is retained as a deferred fallback only. Scheduled
mailbox polling through Gmail or IMAP is retained as the final fallback only if
webhook-style inbound delivery is unavailable.

The machine-readable contract is
`config/courts_nz_email_ingress.json`.

## Dedicated Address
The planned dedicated subscription address is:

```text
courts-nz-judgments@archive.edithatogo.com
```

This address is marked `pending_external_setup` until it exists in Cloudflare
Email Routing and is subscribed to the Courts of New Zealand judgments of public
interest notification list. External setup is tracked in
https://github.com/edithatogo/sm-govt-nz/issues/5.

Current domain blocker: `edithatogo.com` has a pending Cloudflare zone, but
public DNS and RDAP returned `NXDOMAIN`/not found on 2026-06-15. The root
domain must be registered and delegated to `jocelyn.ns.cloudflare.com` and
`joel.ns.cloudflare.com`, or this lane must be switched to another registered
domain, before Cloudflare Email Routing can be enabled.

Cost guardrail: the Cloudflare account was checked on 2026-06-15 and showed no
active subscriptions, no payment method on file, no billing address, no billable
usage data, and Workers on the `Free $0` plan. Cloudflare budget alerts are
informational only and do not cap usage, so do not add a payment method,
register a domain, purchase Workers Paid, or enable metered paid products
without explicit approval.

## Default Route
1. Courts of New Zealand sends the subscription email to the dedicated address.
2. Cloudflare Email Routing delivers the message to
   `courts-nz-email-archive`.
3. The Worker calls GitHub `repository_dispatch` with event type
   `courts_nz_email_received`.
4. The `Archive Email` workflow stores raw evidence under
   `historical_archive_raw/email/` and normalized records under
   `historical_archive_normalized/email/`.

## Mailgun Fallback
Use Mailgun inbound parse only if Cloudflare cannot route or parse the
subscription messages reliably.

Mailgun must preserve either raw MIME or complete provider JSON before
normalization. It must call the same GitHub `repository_dispatch` event type as
the Cloudflare Worker and must not introduce a separate archive schema.

## Mailbox Polling Fallback
Use scheduled mailbox polling only if webhook-style delivery is unavailable.

The mailbox must be dedicated to this archive lane. Polling must archive unseen
messages through `scripts/archive_email_payload.py`, preserve raw evidence
before normalization, and avoid touching `conductor/state.json` or any outbound
posting queue.

## Guardrails
- Email ingress is archive-only.
- Email records must not publish directly to X, Bluesky, Threads, Instagram,
  Facebook, LinkedIn, or any other mirror account.
- Email records must not advance outbound syndication state.
- All routes must deduplicate by message ID, canonical URL, and content hash.
- Any fallback activation needs a separate task commit and review note.
- Any cost-bearing Cloudflare change needs explicit approval before it is made.
