# Manual/API Source Onboarding

Generated: 2026-08-14T16:28:25+00:00
Next batch limit: 25

## Summary

- `selected_sources`: 1254
- `remaining_group_count`: 4
- `remaining_source_count`: 917

## Remaining groups

- `facebook`: 327
- `instagram`: 183
- `newsletter`: 404
- `threads`: 3

## Platform status

- `facebook`: {'needs_authorized_seed_or_api': 327}
- `instagram`: {'needs_authorized_seed_or_api': 183}
- `linkedin`: {'public_fallback_available': 258}
- `newsletter`: {'needs_authorized_seed_or_api': 404}
- `threads`: {'needs_authorized_seed_or_api': 3}
- `x`: {'seed_present': 79}

## Next deterministic batch

| Platform | Source | Agency | Preferred seed path |
| --- | --- | --- | --- |
| `threads` | `nz-police-threads-newzealandpolice` | New Zealand Police (Ngā Pirihimana o Aotearoa) | `manual_archive_seeds/threads/nz-police-threads-newzealandpolice.json` |
| `threads` | `nzte-threads-nzte` | New Zealand Trade and Enterprise (Te Taurapa Tūhono) | `manual_archive_seeds/threads/nzte-threads-nzte.json` |
| `threads` | `wellington-city-libraries-threads-wcl-library` | Wellington City Libraries | `manual_archive_seeds/threads/wellington-city-libraries-threads-wcl-library.json` |
| `newsletter` | `accident-compensation-corporation-newsletter-615b7031` | Accident Compensation Corporation (Te Kaporeihana Āwhina Hunga Whara) | `manual_archive_seeds/newsletter/accident-compensation-corporation-newsletter-615b7031.json` |
| `newsletter` | `accident-compensation-corporation-newsletter-a2c2ad5b` | Accident Compensation Corporation (Te Kaporeihana Āwhina Hunga Whara) | `manual_archive_seeds/newsletter/accident-compensation-corporation-newsletter-a2c2ad5b.json` |
| `newsletter` | `creative-nz-newsletter-7844e992` | Arts Council of New Zealand (Creative New Zealand) | `manual_archive_seeds/newsletter/creative-nz-newsletter-7844e992.json` |
| `newsletter` | `buller-district-council-newsletter-0ccf7aef` | Buller District Council | `manual_archive_seeds/newsletter/buller-district-council-newsletter-0ccf7aef.json` |
| `newsletter` | `buller-district-council-newsletter-70d4a94b` | Buller District Council | `manual_archive_seeds/newsletter/buller-district-council-newsletter-70d4a94b.json` |
| `newsletter` | `cancer-control-agency-newsletter-000607de` | Cancer Control Agency (Te Aho o Te Kahu) | `manual_archive_seeds/newsletter/cancer-control-agency-newsletter-000607de.json` |
| `newsletter` | `central-hawkes-bay-district-council-newsletter-26505743` | Central Hawke's Bay District Council | `manual_archive_seeds/newsletter/central-hawkes-bay-district-council-newsletter-26505743.json` |
| `newsletter` | `central-hawkes-bay-district-council-newsletter-40658a9a` | Central Hawke's Bay District Council | `manual_archive_seeds/newsletter/central-hawkes-bay-district-council-newsletter-40658a9a.json` |
| `newsletter` | `central-otago-district-council-newsletter-196ab35e` | Central Otago District Council | `manual_archive_seeds/newsletter/central-otago-district-council-newsletter-196ab35e.json` |
| `newsletter` | `central-otago-district-council-newsletter-1b76707f` | Central Otago District Council | `manual_archive_seeds/newsletter/central-otago-district-council-newsletter-1b76707f.json` |
| `newsletter` | `central-otago-district-council-newsletter-2eb9c5d4` | Central Otago District Council | `manual_archive_seeds/newsletter/central-otago-district-council-newsletter-2eb9c5d4.json` |
| `newsletter` | `central-otago-district-council-newsletter-36ce28ba` | Central Otago District Council | `manual_archive_seeds/newsletter/central-otago-district-council-newsletter-36ce28ba.json` |
| `newsletter` | `central-otago-district-council-newsletter-3a3e3d51` | Central Otago District Council | `manual_archive_seeds/newsletter/central-otago-district-council-newsletter-3a3e3d51.json` |
| `newsletter` | `central-otago-district-council-newsletter-4defb29a` | Central Otago District Council | `manual_archive_seeds/newsletter/central-otago-district-council-newsletter-4defb29a.json` |
| `newsletter` | `central-otago-district-council-newsletter-557266f6` | Central Otago District Council | `manual_archive_seeds/newsletter/central-otago-district-council-newsletter-557266f6.json` |
| `newsletter` | `central-otago-district-council-newsletter-66a8656c` | Central Otago District Council | `manual_archive_seeds/newsletter/central-otago-district-council-newsletter-66a8656c.json` |
| `newsletter` | `central-otago-district-council-newsletter-7391c51d` | Central Otago District Council | `manual_archive_seeds/newsletter/central-otago-district-council-newsletter-7391c51d.json` |
| `newsletter` | `central-otago-district-council-newsletter-74c66c40` | Central Otago District Council | `manual_archive_seeds/newsletter/central-otago-district-council-newsletter-74c66c40.json` |
| `newsletter` | `central-otago-district-council-newsletter-b115489d` | Central Otago District Council | `manual_archive_seeds/newsletter/central-otago-district-council-newsletter-b115489d.json` |
| `newsletter` | `central-otago-district-council-newsletter-bf4edb9f` | Central Otago District Council | `manual_archive_seeds/newsletter/central-otago-district-council-newsletter-bf4edb9f.json` |
| `newsletter` | `central-otago-district-council-newsletter-d8acb969` | Central Otago District Council | `manual_archive_seeds/newsletter/central-otago-district-council-newsletter-d8acb969.json` |
| `newsletter` | `central-otago-district-council-newsletter-de23a81e` | Central Otago District Council | `manual_archive_seeds/newsletter/central-otago-district-council-newsletter-de23a81e.json` |

## Notes

- This queue is for Facebook, Instagram, Threads, LinkedIn, X, and newsletters.
- `seed_present` sources are ready for archival processing.
- `needs_authorized_seed_or_api` sources remain in the manual/API remainder set.
- `conductor/manual_seed_work_queue.json` lists the remaining sources in deterministic execution order with preferred seed paths.
- `conductor/manual_seed_next_batch_templates.json` contains source-specific starter JSON for the next deterministic batch without creating live seed files.
- The next-batch size is configurable via the `next_batch_limit` workflow input and CLI flag.
