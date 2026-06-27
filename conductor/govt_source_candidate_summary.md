# Government Source Discovery Summary

Generated: 2026-06-27T17:42:11+00:00

## Coverage

- Agencies: 252
- Agencies without known social profiles: 34
- Known registry social profiles: 440
- Candidate records: 3645
- Archive manifest sources: 1700

## Candidates by Platform

- bluesky: 5
- facebook: 296
- instagram: 163
- linkedin: 241
- newsletter: 165
- rss: 2291
- website_page: 247
- x: 79
- youtube: 158

## Candidates by Archive Status

- candidate: 1031
- degraded: 82
- manual_seed: 258
- ready: 329

## Operational Notes

- RSS, public website pages, and Bluesky are the highest-priority automated archive lanes.
- YouTube is listed as candidate until channel handles are resolved to stable channel feeds.
- Meta platforms should use Graph/Threads APIs or authorized exports; avoid brittle unauthenticated scraping.
- LinkedIn and X are retained in the manifest with lower feasibility so archive work can proceed from approved exports or public archive sources.
- `conductor/govt_source_candidate_report.json` contains the exhaustive candidate-level detail for review and onboarding.
