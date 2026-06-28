# Government Source Discovery Summary

Generated: 2026-06-28T21:00:56+00:00

## Coverage

- Agencies: 253
- Agencies without known social profiles: 33
- Known registry social profiles: 443
- Candidate records: 5139
- Archive manifest sources: 2511

## Candidates by Platform

- api: 13
- bluesky: 6
- facebook: 294
- instagram: 161
- linkedin: 240
- newsletter: 167
- rss: 3775
- website_page: 248
- x: 79
- youtube: 156

## Candidates by Archive Status

- candidate: 1807
- degraded: 82
- manual_seed: 258
- ready: 364

## Operational Notes

- RSS, public website pages, and Bluesky are the highest-priority automated archive lanes.
- Atom, JSON Feed, WebSub hubs, ActivityPub/WebFinger, public APIs, and microformats are now explicitly detected as reviewable source candidates.
- YouTube is listed as candidate until channel handles are resolved to stable channel feeds.
- Meta platforms should use Graph/Threads APIs or authorized exports; avoid brittle unauthenticated scraping.
- LinkedIn and X are retained in the manifest with lower feasibility so archive work can proceed from approved exports or public archive sources.
- `conductor/govt_source_candidate_report.json` contains the exhaustive candidate-level detail for review and onboarding.
