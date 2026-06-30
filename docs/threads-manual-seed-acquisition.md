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

## Automated workflow

The repository does not rely on manual workflow dispatch for Threads archival.
Scheduled workflows refresh readiness, open or update GitHub issues for missing
or invalid seed inputs, validate any seed JSON that appears under
`manual_archive_seeds/threads/`, and archive valid seeds automatically.

The only external input is the authorized seed JSON itself. Once a seed file is
committed at a listed source-specific or agency-level path, automation handles
validation, archival, normalized record creation, report commits, and inclusion
in the next monthly cumulative corpus release.

## Readiness reporting

Run `scripts/build_threads_seed_readiness_report.py` locally if needed. In
normal operation the scheduled `Validate Threads Manual Seeds` workflow refreshes:

- `conductor/threads_seed_readiness_report.json`
- `conductor/threads_seed_readiness_summary.md`

Readiness statuses:

- `seed_missing`: no source-specific or agency-level seed JSON is present.
- `seed_empty`: a seed file is present but contains no posts.
- `seed_invalid`: a seed file is present but failed validation.
- `ready_to_archive`: at least one valid post is ready for archival.

## Current registered seed filenames

- `manual_archive_seeds/threads/nz-police-threads-newzealandpolice.json`
- `manual_archive_seeds/threads/nzte-threads-nzte.json`
- `manual_archive_seeds/threads/wellington-city-libraries-threads-wcl-library.json`

