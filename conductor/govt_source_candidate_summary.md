# Government Source Discovery Summary

Generated: 2026-07-27T18:51:04+00:00

## Coverage

- Agencies: 256
- Agencies without known social profiles: 33
- Known registry social profiles: 445
- Candidate records: 5246
- Archive manifest sources: 5676

## Candidates by Platform

- api: 13
- bluesky: 18
- facebook: 290
- instagram: 161
- linkedin: 234
- medium: 2
- newsletter: 159
- rss: 3827
- website_page: 311
- x: 74
- youtube: 157

## Candidates by Archive Status

- candidate: 1111
- degraded: 83
- manual_seed: 258
- ready: 4224

## Operational Notes

- RSS, public website pages, and Bluesky are the highest-priority automated archive lanes.
- Atom, JSON Feed, WebSub hubs, ActivityPub/WebFinger, public APIs, and microformats are now explicitly detected as reviewable source candidates.
- YouTube is listed as candidate until channel handles are resolved to stable channel feeds.
- Meta platforms should use Graph/Threads APIs or authorized exports; avoid brittle unauthenticated scraping.
- LinkedIn and X are retained in the manifest with lower feasibility so archive work can proceed from approved exports or public archive sources.
- `conductor/govt_source_candidate_report.json` contains the exhaustive candidate-level detail for review and onboarding.
