# Manual Seed Intake

Manual seeds are operator-authorized JSON inputs for platforms where direct public capture is unavailable or intentionally disabled.

## Supported seed directories

- `manual_archive_seeds/threads/`
- `manual_archive_seeds/linkedin/`
- `manual_archive_seeds/newsletter/`
- `manual_archive_seeds/x/`
- `manual_archive_seeds/youtube/`
- `manual_archive_seeds/facebook/`
- `manual_archive_seeds/instagram/`

Each seed file should be named with the registered `source_id` when possible, falling back to `agency_id`.

## Required JSON shape

```json
{
  "posts": [
    {
      "post_id": "stable-platform-id-or-operator-id",
      "url": "https://example.govt.nz/or/platform/post",
      "created_at": "2026-07-01T00:00:00Z",
      "text": "Archived public or operator-authorized content.",
      "media": [
        {
          "url": "https://example.govt.nz/media.jpg",
          "media_type": "image",
          "alt_text": "Optional description"
        }
      ]
    }
  ]
}
```

## Current gap interpretation

- `manual_seed_missing` is a tracked zero-input state, not a workflow failure.
- Threads, LinkedIn, and newsletters are already wired to ingest seeds when files appear.
- Logged-in, private, cookie, local storage, and hidden GraphQL data must not be extracted into seed files unless separately authorized and documented.

## Validation statuses

- `manual_seed_missing`: no seed file exists yet; this is report-only coverage tracking.
- `seed_empty`: a seed file exists and is valid JSON, but contains no posts; replace it with an authorized export containing records.
- `seed_invalid`: a seed file exists but failed JSON or required-field validation; fix the file shape before archival can proceed.
- `manual_seed_captured`: valid seed posts were written to raw and normalized archive paths.

Synthetic fixtures for the accepted shape are stored under `tests/fixtures/manual_archive_seeds/` for Threads, LinkedIn, and newsletter inputs. These are not real public records and exist only to keep parser expectations deterministic.

## Newsletter payload ingestion

Newsletter payloads can also be supplied as JSON or `.eml` files under `manual_archive_seeds/newsletter_payloads/` and processed with `scripts/archive_newsletter_payloads.py` or the `Archive Newsletter Payloads` workflow.

Supported JSON fields include `source_id`, `agency_id`, `message_id`, `from`, `to`, `subject`, `text`, `html`, `received_at`, `links`, `raw_mime`, and `raw_mime_base64`. Matching is deterministic: `source_id` is preferred, then `agency_id`. Unmatched registered newsletter sources report `missing_payload`; malformed payload files report `payload_invalid`.

The workflow does not configure a mailbox or subscribe to sources. It only archives operator-provided payload files and is safe to run without email-provider credentials.
