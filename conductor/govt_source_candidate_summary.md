# Government Source Discovery Summary

Generated: 2026-07-02T14:55:49+00:00

## Coverage

- Agencies: 255
- Agencies without known social profiles: 33
- Known registry social profiles: 444
- Candidate records: 5237
- Archive manifest sources: 1854

## Candidates by Platform

- api: 13
- bluesky: 18
- facebook: 292
- instagram: 162
- linkedin: 234
- newsletter: 162
- rss: 3811
- website_page: 313
- x: 76
- youtube: 156

## Candidates by Archive Status

- candidate: 1063
- degraded: 83
- manual_seed: 256
- ready: 452

## Operational Notes

- RSS, public website pages, and Bluesky are the highest-priority automated archive lanes.
- Atom, JSON Feed, WebSub hubs, ActivityPub/WebFinger, public APIs, and microformats are now explicitly detected as reviewable source candidates.
- YouTube is listed as candidate until channel handles are resolved to stable channel feeds.
- Meta platforms should use Graph/Threads APIs or authorized exports; avoid brittle unauthenticated scraping.
- LinkedIn and X are retained in the manifest with lower feasibility so archive work can proceed from approved exports or public archive sources.
- `conductor/govt_source_candidate_report.json` contains the exhaustive candidate-level detail for review and onboarding.
