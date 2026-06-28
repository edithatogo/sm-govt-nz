# Government Source Discovery Summary

Generated: 2026-06-28T13:56:07+00:00

## Coverage

- Agencies: 252
- Agencies without known social profiles: 34
- Known registry social profiles: 482
- Candidate records: 4442
- Archive manifest sources: 1700

## Candidates by Platform

- bluesky: 4
- facebook: 176
- instagram: 76
- linkedin: 128
- newsletter: 1
- rss: 3705
- website_page: 247
- x: 46
- youtube: 59

## Candidates by Archive Status

- candidate: 1031
- degraded: 82
- manual_seed: 258
- ready: 329

## Operational Notes

- RSS, public website pages, and Bluesky are the highest-priority automated archive lanes.
- Atom, JSON Feed, WebSub hubs, ActivityPub/WebFinger, public APIs, and microformats are now explicitly detected as reviewable source candidates.
- YouTube is listed as candidate until channel handles are resolved to stable channel feeds.
- Meta platforms should use Graph/Threads APIs or authorized exports; avoid brittle unauthenticated scraping.
- LinkedIn and X are retained in the manifest with lower feasibility so archive work can proceed from approved exports or public archive sources.
- `conductor/govt_source_candidate_report.json` contains the exhaustive candidate-level detail for review and onboarding.
