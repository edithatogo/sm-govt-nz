# Threads seed intake checklist

Use this file to mark which registered Threads sources should be included in the next manual seed intake batch.

The current archive state for all three is `manual_seed_missing`. The expected seed directory is `manual_archive_seeds/threads/`.

## Candidate sources

| Include | Source ID | Agency | Handle | URL | Preferred seed file | Fallback seed file |
| --- | --- | --- | --- | --- | --- | --- |
| [ ] | `nz-police-threads-newzealandpolice` | New Zealand Police (Ngā Pirihimana o Aotearoa) | `@newzealandpolice` | `https://www.threads.net/@newzealandpolice` | `manual_archive_seeds/threads/nz-police-threads-newzealandpolice.json` | `manual_archive_seeds/threads/nz-police.json` |
| [ ] | `nzte-threads-nzte` | New Zealand Trade and Enterprise (Te Taurapa Tūhono) | `@nzte` | `https://www.threads.net/@nzte` | `manual_archive_seeds/threads/nzte-threads-nzte.json` | `manual_archive_seeds/threads/nz-trade-and-enterprise.json` |
| [ ] | `wellington-city-libraries-threads-wcl-library` | Wellington City Libraries | `@wcl_library` | `https://www.threads.net/@wcl_library` | `manual_archive_seeds/threads/wellington-city-libraries-threads-wcl-library.json` | `manual_archive_seeds/threads/wellington-city-libraries.json` |

## Seed JSON shape

Each seed file should contain either:

```json
{
  "posts": [
    {
      "post_id": "example-thread-post-id",
      "url": "https://www.threads.net/@example/post/example",
      "canonical_url": "https://www.threads.net/@example/post/example",
      "created_at": "2026-01-01T00:00:00+00:00",
      "account": "example",
      "text": "Example Threads post text from an authorized export.",
      "media": [
        {
          "url": "https://example.invalid/media.jpg",
          "media_type": "image",
          "alt_text": "Optional media description"
        }
      ]
    }
  ]
}
```

or a bare array of post objects with the same fields.

## Required fields per post

- `url`
- `created_at`
- `text`

## Optional fields per post

- `post_id`
- `canonical_url`
- `account`
- `media`

## Operator notes

- Mark `[x]` only for sources you want included in the intake batch.
- Keep `created_at` in ISO 8601.
- Do not fabricate placeholder posts.
- Once seed files exist, run `Validate Threads Manual Seeds` and then `Archive Threads Manual Seeds`.
