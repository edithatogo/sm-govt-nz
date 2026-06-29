# Government Source Discovery Summary

Generated: 2026-06-29T10:22:59+00:00

## Coverage

- Agencies: 255
- Agencies without known social profiles: 33
- Known registry social profiles: 445
- Candidate records: 5247
- Archive manifest sources: 1835

## Candidates by Platform

- api: 13
- bluesky: 18
- facebook: 294
- instagram: 162
- linkedin: 236
- newsletter: 164
- rss: 3811
- website_page: 316
- x: 76
- youtube: 157

## Candidates by Archive Status

- candidate: 1051
- degraded: 79
- manual_seed: 255
- ready: 450

## Operational Notes

- RSS, public website pages, and Bluesky are the highest-priority automated archive lanes.
- Atom, JSON Feed, WebSub hubs, ActivityPub/WebFinger, public APIs, and microformats are now explicitly detected as reviewable source candidates.
- YouTube is listed as candidate until channel handles are resolved to stable channel feeds.
- Meta platforms should use Graph/Threads APIs or authorized exports; avoid brittle unauthenticated scraping.
- LinkedIn and X are retained in the manifest with lower feasibility so archive work can proceed from approved exports or public archive sources.
- `conductor/govt_source_candidate_report.json` contains the exhaustive candidate-level detail for review and onboarding.
