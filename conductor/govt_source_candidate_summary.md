# Government Source Discovery Summary

Generated: 2026-06-30T18:24:20+00:00

## Coverage

- Agencies: 255
- Agencies without known social profiles: 33
- Known registry social profiles: 445
- Candidate records: 5198
- Archive manifest sources: 1841

## Candidates by Platform

- api: 13
- bluesky: 18
- facebook: 289
- instagram: 159
- linkedin: 232
- newsletter: 146
- rss: 3809
- website_page: 301
- x: 76
- youtube: 155

## Candidates by Archive Status

- candidate: 1056
- degraded: 79
- manual_seed: 256
- ready: 450

## Operational Notes

- RSS, public website pages, and Bluesky are the highest-priority automated archive lanes.
- Atom, JSON Feed, WebSub hubs, ActivityPub/WebFinger, public APIs, and microformats are now explicitly detected as reviewable source candidates.
- YouTube is listed as candidate until channel handles are resolved to stable channel feeds.
- Meta platforms should use Graph/Threads APIs or authorized exports; avoid brittle unauthenticated scraping.
- LinkedIn and X are retained in the manifest with lower feasibility so archive work can proceed from approved exports or public archive sources.
- `conductor/govt_source_candidate_report.json` contains the exhaustive candidate-level detail for review and onboarding.
