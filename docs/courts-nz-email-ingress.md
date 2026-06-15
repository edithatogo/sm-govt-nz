# Courts of New Zealand Email Ingress

## GitHub Receiver

The `Archive Email` workflow receives email notifications through GitHub
`repository_dispatch` events of type `courts_nz_email_received`.

The default route, fallback order, planned dedicated address, and archive-only
guardrails are recorded in `config/courts_nz_email_ingress.json`. The fallback
decision note is `docs/courts-nz-email-ingress-fallbacks.md`.

The dispatch `client_payload` should be a JSON object with these fields:

- `message_id`: source email message ID.
- `from`: sender header.
- `to`: destination header.
- `subject`: email subject.
- `text`: plain-text body, if available.
- `html`: HTML body, if available.
- `received_at`: ISO 8601 timestamp.
- `links`: optional list of URLs extracted by the sender or worker.
- `raw_mime_base64`: optional base64 encoded raw email.

`scripts/archive_email_payload.py` stores raw email evidence under
`historical_archive_raw/email/<yyyy-mm>/` and appends a normalized record to
`historical_archive_normalized/email/<yyyy-mm>.jsonl`.

## Zero-Cost Manual Fallback

While the dedicated Cloudflare-routed address is blocked by domain ownership or
delegation, the `Archive Email` workflow can be run manually with
`workflow_dispatch`. Paste the same JSON payload shape into the `payload_json`
input.

This route is active, costs $0, and preserves the same archive-only contract as
the Cloudflare route. It is suitable for capturing Courts of NZ subscription
messages that are received through another mailbox and manually exported or
forwarded into JSON form.

## Cloudflare Email Routing Worker

Cloudflare should forward the dedicated subscription address to a Worker. The
Worker should call:

```text
POST https://api.github.com/repos/edithatogo/sm-govt-nz/dispatches
```

Required GitHub request body:

```json
{
  "event_type": "courts_nz_email_received",
  "client_payload": {
    "message_id": "<message-id>",
    "from": "sender@example.test",
    "to": "archive@example.test",
    "subject": "Judgment of public interest",
    "text": "Plain text body",
    "html": "<p>HTML body</p>",
    "received_at": "2026-06-14T00:00:00Z",
    "links": ["https://www.courtsofnz.govt.nz/"],
    "raw_mime_base64": "..."
  }
}
```

The Worker needs a GitHub fine-grained token with permission to dispatch events
to this repository. Store it as a Cloudflare Worker secret, not in this repo.

This repository includes a deployable Worker template:

- Worker module: `cloudflare/courts_nz_email_worker.mjs`
- Wrangler example: `cloudflare/wrangler.courts-nz-email.toml.example`
- Worker tests: `cloudflare/courts_nz_email_worker.test.mjs`

Setup outline:

1. Add repository secrets for the manual `Deploy Email Worker` workflow:

   - `CLOUDFLARE_API_TOKEN`
   - `CLOUDFLARE_ACCOUNT_ID`
   - `EMAIL_WORKER_GITHUB_TOKEN`

2. Run the `Deploy Email Worker` workflow with the dedicated subscription
   address in `allowed_recipients`.
3. Register or delegate the root domain for the dedicated address. Current
   target state is recorded in `config/courts_nz_email_ingress.json`:

   - root domain: `edithatogo.com`
   - dedicated subdomain: `archive.edithatogo.com`
   - Cloudflare nameservers: `jocelyn.ns.cloudflare.com`,
     `joel.ns.cloudflare.com`

   As of 2026-06-15, public DNS and RDAP returned `NXDOMAIN`/not found for
   `edithatogo.com`, so the domain must be registered or this lane must be
   switched to a registered domain before Email Routing can become active.
   Domain registration is cost-bearing and must not be done without explicit
   approval. The Cloudflare account was verified on 2026-06-15 as having no
   active subscriptions, no payment method, no billing address, no billable
   usage data, and Workers on the `Free $0` plan.
4. In Cloudflare Email Routing, keep the staged routing rule disabled until the
   domain/DNS gate is cleared:

   - CLI: `npx -y wrangler`
   - Wrangler version: `4.100.0`
   - Account ID: `16f3035fe42afb94d9138f86a8672ae5`
   - Rule ID: `4fbe93480e834fd786a1959020c8a526`
   - Rule name: `CourtsNZJudgmentsArchiveWorker`
   - Matcher: `to:courts-nz-judgments@archive.edithatogo.com`
   - Action: `worker:courts-nz-email-archive`
   - Enabled: `false`
   - Verification command:
     `npx -y wrangler email routing rules get edithatogo.com 4fbe93480e834fd786a1959020c8a526`

   Cloudflare Email Routing for `edithatogo.com` was verified with Wrangler on
   2026-06-15 as `Enabled: false` and `Status: unconfigured`. Do not enable
   this rule until the domain is registered/delegated and the required MX/TXT
   records are in place.
5. Subscribe the dedicated address to the Courts of New Zealand judgments of
   public interest notification list, then update
   `config/courts_nz_email_ingress.json` from `pending_external_setup` to
   `active`.

External setup for the dedicated address is tracked in
https://github.com/edithatogo/sm-govt-nz/issues/5.

For local deployment, copy `cloudflare/wrangler.courts-nz-email.toml.example`
to `cloudflare/wrangler.toml`, replace `ALLOWED_RECIPIENTS`, and set
`GITHUB_TOKEN` as a Worker secret:

   ```powershell
   wrangler secret put GITHUB_TOKEN
   ```

Then deploy from the `cloudflare/` directory with `wrangler deploy`.

The template is based on Cloudflare's Email Workers API, which exposes an
`email(message, env, ctx)` handler, `message.headers`, `message.raw`, envelope
sender/recipient fields, and `message.setReject()`. Cloudflare's local routing
docs describe testing Email Workers through the `/cdn-cgi/handler/email`
endpoint with a raw RFC 5322 message.

## Guardrails

- Email records are archive-only corpus inputs.
- Email records must not advance outbound syndication cursors.
- Email records must not create posts directly on X, Bluesky, Threads, or any
  other mirror account.
- If a payload is malformed, the workflow should fail before committing partial
  archive files.
- Cloudflare setup must stay on free plans. Do not add a payment method, buy a
  domain, purchase Workers Paid, or enable metered paid products without
  explicit approval.
