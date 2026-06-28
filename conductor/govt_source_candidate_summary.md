# Government Source Discovery Summary

Generated: 2026-06-28T15:06:52+00:00

## Coverage

- Agencies: 252
- Agencies without known social profiles: 33
- Known registry social profiles: 480
- Candidate records: 4487
- Archive manifest sources: 2495

## Candidates by Platform

- bluesky: 5
- facebook: 186
- instagram: 83
- linkedin: 134
- newsletter: 8
- rss: 3710
- website_page: 247
- x: 50
- youtube: 64

## Candidates by Archive Status

- candidate: 1807
- degraded: 82
- manual_seed: 258
- ready: 348

## Operational Notes

- RSS, public website pages, and Bluesky are the highest-priority automated archive lanes.
- Atom, JSON Feed, WebSub hubs, ActivityPub/WebFinger, public APIs, and microformats are now explicitly detected as reviewable source candidates.
- YouTube is listed as candidate until channel handles are resolved to stable channel feeds.
- Meta platforms should use Graph/Threads APIs or authorized exports; avoid brittle unauthenticated scraping.
- LinkedIn and X are retained in the manifest with lower feasibility so archive work can proceed from approved exports or public archive sources.
- `conductor/govt_source_candidate_report.json` contains the exhaustive candidate-level detail for review and onboarding.
