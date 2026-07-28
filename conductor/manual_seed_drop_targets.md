# Manual Seed Drop Targets

Use these paths to place operator-authorized seed JSON files for the next deterministic batch.
The templates below are derived from `conductor/manual_seed_next_batch_templates.json` and do not create live seed files by themselves.

Generated: 2026-07-28T17:05:42+00:00

## Summary

- `template_count`: 25
- `limit`: 25

| Platform | Source | Seed path |
| --- | --- | --- |
| `threads` | `nz-police-threads-newzealandpolice` | `manual_archive_seeds/threads/nz-police-threads-newzealandpolice.json` |
| `threads` | `nzte-threads-nzte` | `manual_archive_seeds/threads/nzte-threads-nzte.json` |
| `threads` | `wellington-city-libraries-threads-wcl-library` | `manual_archive_seeds/threads/wellington-city-libraries-threads-wcl-library.json` |
| `newsletter` | `accident-compensation-corporation-newsletter-a2c2ad5b` | `manual_archive_seeds/newsletter/accident-compensation-corporation-newsletter-a2c2ad5b.json` |
| `newsletter` | `creative-nz-newsletter-7844e992` | `manual_archive_seeds/newsletter/creative-nz-newsletter-7844e992.json` |
| `newsletter` | `buller-district-council-newsletter-70d4a94b` | `manual_archive_seeds/newsletter/buller-district-council-newsletter-70d4a94b.json` |
| `newsletter` | `cancer-control-agency-newsletter-000607de` | `manual_archive_seeds/newsletter/cancer-control-agency-newsletter-000607de.json` |
| `newsletter` | `central-hawkes-bay-district-council-newsletter-26505743` | `manual_archive_seeds/newsletter/central-hawkes-bay-district-council-newsletter-26505743.json` |
| `newsletter` | `central-hawkes-bay-district-council-newsletter-40658a9a` | `manual_archive_seeds/newsletter/central-hawkes-bay-district-council-newsletter-40658a9a.json` |
| `newsletter` | `central-otago-district-council-newsletter-196ab35e` | `manual_archive_seeds/newsletter/central-otago-district-council-newsletter-196ab35e.json` |
| `newsletter` | `central-otago-district-council-newsletter-1b76707f` | `manual_archive_seeds/newsletter/central-otago-district-council-newsletter-1b76707f.json` |
| `newsletter` | `central-otago-district-council-newsletter-2eb9c5d4` | `manual_archive_seeds/newsletter/central-otago-district-council-newsletter-2eb9c5d4.json` |
| `newsletter` | `central-otago-district-council-newsletter-36ce28ba` | `manual_archive_seeds/newsletter/central-otago-district-council-newsletter-36ce28ba.json` |
| `newsletter` | `central-otago-district-council-newsletter-3a3e3d51` | `manual_archive_seeds/newsletter/central-otago-district-council-newsletter-3a3e3d51.json` |
| `newsletter` | `central-otago-district-council-newsletter-4defb29a` | `manual_archive_seeds/newsletter/central-otago-district-council-newsletter-4defb29a.json` |
| `newsletter` | `central-otago-district-council-newsletter-557266f6` | `manual_archive_seeds/newsletter/central-otago-district-council-newsletter-557266f6.json` |
| `newsletter` | `central-otago-district-council-newsletter-66a8656c` | `manual_archive_seeds/newsletter/central-otago-district-council-newsletter-66a8656c.json` |
| `newsletter` | `central-otago-district-council-newsletter-7391c51d` | `manual_archive_seeds/newsletter/central-otago-district-council-newsletter-7391c51d.json` |
| `newsletter` | `central-otago-district-council-newsletter-74c66c40` | `manual_archive_seeds/newsletter/central-otago-district-council-newsletter-74c66c40.json` |
| `newsletter` | `central-otago-district-council-newsletter-b115489d` | `manual_archive_seeds/newsletter/central-otago-district-council-newsletter-b115489d.json` |
| `newsletter` | `central-otago-district-council-newsletter-bf4edb9f` | `manual_archive_seeds/newsletter/central-otago-district-council-newsletter-bf4edb9f.json` |
| `newsletter` | `central-otago-district-council-newsletter-d8acb969` | `manual_archive_seeds/newsletter/central-otago-district-council-newsletter-d8acb969.json` |
| `newsletter` | `central-otago-district-council-newsletter-de23a81e` | `manual_archive_seeds/newsletter/central-otago-district-council-newsletter-de23a81e.json` |
| `newsletter` | `chatham-islands-council-newsletter-1e57736f` | `manual_archive_seeds/newsletter/chatham-islands-council-newsletter-1e57736f.json` |
| `newsletter` | `chatham-islands-council-newsletter-fdb26d29` | `manual_archive_seeds/newsletter/chatham-islands-council-newsletter-fdb26d29.json` |

## Shape

```json
{
  "account": "newzealandpolice",
  "agency_id": "nz-police",
  "agency_name": "New Zealand Police (Ng\u0101 Pirihimana o Aotearoa)",
  "authorization_note": "Replace this template with operator-authorized export data before placing it under manual_archive_seeds/.",
  "platform": "threads",
  "posts": [
    {
      "created_at": "2026-07-01T00:00:00Z",
      "media": [
        {
          "alt_text": "Optional description",
          "media_type": "image",
          "url": "https://example.govt.nz/media.jpg"
        }
      ],
      "post_id": "stable-platform-id-or-operator-id",
      "text": "Archived public or operator-authorized content.",
      "url": "https://example.govt.nz/or/platform/post"
    }
  ],
  "source_id": "nz-police-threads-newzealandpolice",
  "source_url": "https://www.threads.net/@newzealandpolice",
  "target_path": "manual_archive_seeds/threads/nz-police-threads-newzealandpolice.json"
}
```
