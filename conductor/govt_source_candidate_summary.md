# Government Source Discovery Summary

Generated: 2026-08-07T18:06:58+00:00

## Coverage

- Agencies: 256
- Agencies without known social profiles: 33
- Known registry social profiles: 450
- Candidate records: 5198
- Archive manifest sources: 5707

## Candidates by Platform

- api: 12
- bluesky: 18
- facebook: 285
- instagram: 160
- linkedin: 229
- medium: 2
- newsletter: 139
- rss: 3827
- website_page: 298
- x: 72
- youtube: 156

## Candidates by Archive Status

- candidate: 1131
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
