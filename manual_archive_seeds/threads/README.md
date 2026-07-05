# Threads manual seed exports

Live public Threads archive capture is supported through the official Threads
API when a personal Threads account token is available in the GitHub Actions
secret `THREADS_ACCESS_TOKEN` and `THREADS_API_CAPTURE_ENABLED=true` is set as
the repo variable. Until that is deliberately enabled, archive registered
Threads sources through operator-authorized seed exports.

## Live API enablement

To turn on ongoing Threads archiving:

1. Store the personal-account token in the `THREADS_ACCESS_TOKEN` GitHub secret.
2. Set the repository variable `THREADS_API_CAPTURE_ENABLED` to `true`.
3. Keep `THREADS_API_BASE_URL` at the default unless the API endpoint changes.
4. Run `Archive Threads Scheduled` or `Validate Threads Manual Seeds` as needed.

## Seed file locations

Use one JSON file per source. Source-specific filenames are preferred:

- `manual_archive_seeds/threads/nz-police-threads-newzealandpolice.json`
- `manual_archive_seeds/threads/nzte-threads-nzte.json`
- `manual_archive_seeds/threads/wellington-city-libraries-threads-wcl-library.json`

Agency-level fallback filenames are also accepted:

- `manual_archive_seeds/threads/nz-police.json`
- `manual_archive_seeds/threads/nz-trade-and-enterprise.json`
- `manual_archive_seeds/threads/wellington-city-libraries.json`

## JSON shape

Use `README.template.json` as the schema guide. The file may contain either a
top-level `posts` array or a bare array of post objects.

Each post should include:

- `url`
- `created_at`
- `text`

Optional fields:

- `post_id`
- `canonical_url`
- `account`
- `media`

## Intake checklist

Only add records that come from an operator-authorized export or bounded capture.
Do not fabricate placeholder posts and do not scrape around access controls.

For each registered source:

1. Create the source-specific JSON file listed above.
2. Record each post with its public URL, original created timestamp, and text.
3. Include media URLs and alt text when they are visible in the authorized
   export or capture.
4. Preserve the source account handle in `account`.
5. Keep `created_at` in ISO 8601 format, including a timezone offset when known.
6. Run validation before archiving.

The validator rejects duplicate records within a seed file, malformed Threads
URLs, non-Threads canonical URLs, invalid timestamps, and mismatches between a
known source filename and the account handle in `url`, `canonical_url`, or
`account`. It accepts empty seed files only when the validation workflow is run
with `--allow-empty`, which is used for readiness checks before seed exports
exist.

Example minimal file:

```json
{
  "posts": [
    {
      "url": "https://www.threads.net/@newzealandpolice/post/example",
      "created_at": "2026-06-01T12:00:00+12:00",
      "account": "newzealandpolice",
      "text": "Post text from an authorized export or bounded capture."
    }
  ]
}
```

## Validation and archive workflows

Run `Validate Threads Manual Seeds` after adding or changing seed files.

Run `Archive Threads Manual Seeds` to normalize and archive valid seed exports.

The scheduled `Archive Threads Scheduled` workflow uses the official Threads API
when the personal-account gate is enabled, and otherwise falls back to a matching
manual seed.
