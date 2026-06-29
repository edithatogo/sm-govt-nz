# Threads Manual Seed Acquisition Checklist

This project does not use live public Threads profile capture unless the
official Meta permission path is deliberately completed. Until then, Threads
archiving depends on operator-authorized seed exports.

## Acquisition boundary

- Use only account-owner exports, approved API outputs, or bounded captures from
  an operator-authorized browser session.
- Do not bypass access controls, automate login walls, or fabricate placeholder
  posts.
- Keep enough provenance to identify who captured the seed, when it was
  captured, and which public account URL was used.

## Minimum seed fields

Each post should include:

- `url`: the public Threads post URL.
- `created_at`: the original post timestamp in ISO 8601 when available.
- `text`: the visible post text.
- `account`: the source account handle.

Recommended optional fields:

- `post_id`: platform post identifier when available.
- `canonical_url`: canonical public URL if different from `url`.
- `media`: list of visible media URLs and alt text when available.

## Operator workflow

1. Open the official Threads profile URL for the registered source.
2. Capture visible posts through an authorized export or bounded browser session.
3. Save one JSON file under `manual_archive_seeds/threads/<source_id>.json`.
4. Run the `Validate Threads Manual Seeds` workflow.
5. Fix any duplicate, URL, timestamp, account-handle, or media-shape failures.
6. Run `Archive Threads Manual Seeds` after validation passes.

## Current registered seed filenames

- `manual_archive_seeds/threads/nz-police-threads-newzealandpolice.json`
- `manual_archive_seeds/threads/nzte-threads-nzte.json`
- `manual_archive_seeds/threads/wellington-city-libraries-threads-wcl-library.json`

