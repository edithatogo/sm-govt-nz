# Government Source Discovery Summary

Generated: 2026-08-07T17:15:05+00:00

## Coverage

- Agencies: 256
- Agencies without known social profiles: 33
- Known registry social profiles: 446
- Candidate records: 5254
- Archive manifest sources: 5708

## Candidates by Platform

- api: 13
- bluesky: 18
- facebook: 292
- instagram: 163
- linkedin: 236
- medium: 2
- newsletter: 158
- rss: 3830
- website_page: 311
- x: 73
- youtube: 158

## Candidates by Archive Status

- candidate: 1132
- degraded: 83
- manual_seed: 258
- ready: 4235

## Operational Notes

- RSS, public website pages, and Bluesky are the highest-priority automated archive lanes.
- Atom, JSON Feed, WebSub hubs, ActivityPub/WebFinger, public APIs, and microformats are now explicitly detected as reviewable source candidates.
- YouTube is listed as candidate until channel handles are resolved to stable channel feeds.
- Meta platforms should use Graph/Threads APIs or authorized exports; avoid brittle unauthenticated scraping.
- LinkedIn and X are retained in the manifest with lower feasibility so archive work can proceed from approved exports or public archive sources.
- `conductor/govt_source_candidate_report.json` contains the exhaustive candidate-level detail for review and onboarding.
