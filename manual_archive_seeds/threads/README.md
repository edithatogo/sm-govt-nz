# Threads manual seed exports

Live public Threads profile capture is currently gated by Meta business
verification and App Review for `threads_profile_discovery`. Until that is
deliberately completed, archive registered Threads sources through
operator-authorized seed exports.

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

## Validation and archive workflows

Run `Validate Threads Manual Seeds` after adding or changing seed files.

Run `Archive Threads Manual Seeds` to normalize and archive valid seed exports.

The scheduled `Archive Threads Scheduled` workflow also falls back to a matching
manual seed when the official Threads API is unavailable.
