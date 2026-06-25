# Government Source Discovery Summary

Generated: 2026-06-25T03:40:49+00:00

## Coverage

- Agencies: 252
- Agencies without known social profiles: 34
- Known registry social profiles: 427
- Candidate records: 3860
- Archive manifest sources: 1637

## Candidates by Platform

- bluesky: 5
- facebook: 305
- instagram: 173
- linkedin: 250
- newsletter: 333
- rss: 2293
- website_page: 247
- x: 79
- youtube: 175

## Candidates by Archive Status

- candidate: 986
- degraded: 79
- manual_seed: 250
- ready: 322

## Operational Notes

- RSS, public website pages, and Bluesky are the highest-priority automated archive lanes.
- YouTube is listed as candidate until channel handles are resolved to stable channel feeds.
- Meta platforms should use Graph/Threads APIs or authorized exports; avoid brittle unauthenticated scraping.
- LinkedIn and X are retained in the manifest with lower feasibility so archive work can proceed from approved exports or public archive sources.
- `conductor/govt_source_candidate_report.json` contains the exhaustive candidate-level detail for review and onboarding.
