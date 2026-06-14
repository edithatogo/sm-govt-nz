# Courts of New Zealand Email Ingress

## GitHub Receiver

The `Archive Email` workflow receives email notifications through GitHub
`repository_dispatch` events of type `courts_nz_email_received`.

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

## Guardrails

- Email records are archive-only corpus inputs.
- Email records must not advance outbound syndication cursors.
- Email records must not create posts directly on X, Bluesky, Threads, or any
  other mirror account.
- If a payload is malformed, the workflow should fail before committing partial
  archive files.
