# Courts of New Zealand Email Ingress Fallback Decision

## Decision
Cloudflare Email Routing Worker remains the default ingress route for Courts of
New Zealand judgments of public interest subscription messages.

Manual `Archive Email` workflow dispatch is active as the zero-cost operational
fallback while the dedicated Cloudflare-routed address is blocked by domain
ownership or delegation.

Pipedream Email Trigger is the recommended zero-cost automated fallback while
there is no owned domain for Cloudflare Email Routing. Pipedream can provide a
workflow-specific email address, receive the Courts of NZ subscription message,
and call the same GitHub `repository_dispatch` event as the Cloudflare Worker.

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

## Manual Workflow Fallback
Use the manual `Archive Email` workflow dispatch while the dedicated address is
not yet routable. The operator supplies a `payload_json` object with the same
fields as the Cloudflare Worker dispatch payload.

This fallback is active because it does not require a domain, payment method,
paid email routing service, or new platform credentials. It must still preserve
raw evidence before normalization and must not touch outbound syndication
state.

## Pipedream Email Trigger Fallback
Use Pipedream before Mailgun or mailbox polling if an automated zero-cost route
is needed without buying or delegating a domain.

Current setup state, verified on 2026-06-16:

- Status: configured in Pipedream, pending secret, deploy, and test.
- Project: `https://pipedream.com/@edithatogo-workspace/projects/proj_p2sg9bb`
- Workflow: `Courts NZ Judgments Email Archive - Email Trigger`
- Workflow URL:
  `https://pipedream.com/@edithatogo-workspace/projects/proj_p2sg9bb/courts-nz-judgments-email-archive-email-trigger-p_95C2agq/build`
- Generated email address: `em4mkapmjakoh5o@upload.pipedream.net`
- Required secret: `GITHUB_DISPATCH_TOKEN`

Setup contract:

1. Create a Pipedream workflow using the built-in Email trigger.
2. Subscribe the generated Pipedream email address to the Courts of NZ
   judgments of public interest notification list.
3. Add one code/action step that sends:

   ```text
   POST https://api.github.com/repos/edithatogo/sm-govt-nz/dispatches
   ```

   with event type `courts_nz_email_received` and a `client_payload` matching
   the `Archive Email` payload schema.
4. Store the GitHub dispatch token in Pipedream's secret store. Do not commit it
   to this repository.
5. Run one test email and confirm raw and normalized email records are archived.

Volume and cost risk:

- Recent Courts of NZ Bluesky archive volume is 11-14 records per month.
- Courts of NZ RSS records in 2026 are 3-33 records per month.
- Existing email archive volume is 1 test record.
- A dedicated email-trigger workflow should therefore run tens of times per
  month, not hundreds or thousands, unless Courts of NZ publication volume
  changes materially.
- The expected paid-usage risk is low if the workflow remains limited to one
  email trigger plus one GitHub dispatch/code step and does not add long-running
  processing, fan-out posting, AI steps, or broad mailbox ingestion.

Operational guardrail: keep billing disabled/no paid upgrade in Pipedream,
review usage after the first month, and switch back to manual dispatch if the
account approaches the free-tier execution or credit limit.

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
