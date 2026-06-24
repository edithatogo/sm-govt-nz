# Government Source Discovery Summary

Generated: 2026-06-24T12:13:16+00:00

## Coverage

- Agencies: 252
- Agencies without known social profiles: 34
- Known registry social profiles: 483
- Candidate records: 2953
- Archive manifest sources: 730

## Candidates by Platform

- bluesky: 4
- facebook: 175
- instagram: 74
- linkedin: 126
- rss: 2223
- website_page: 247
- x: 46
- youtube: 58

## Candidates by Archive Status

- candidate: 307
- degraded: 46
- manual_seed: 126
- ready: 251

## Operational Notes

- RSS, public website pages, and Bluesky are the highest-priority automated archive lanes.
- YouTube is listed as candidate until channel handles are resolved to stable channel feeds.
- Meta platforms should use Graph/Threads APIs or authorized exports; avoid brittle unauthenticated scraping.
- LinkedIn and X are retained in the manifest with lower feasibility so archive work can proceed from approved exports or public archive sources.
- `conductor/govt_source_candidate_report.json` contains the exhaustive candidate-level detail for review and onboarding.
