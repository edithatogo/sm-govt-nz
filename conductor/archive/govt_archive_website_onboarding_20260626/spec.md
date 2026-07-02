# Spec - NZ Government Archive - multi-agency website page archiving

## Problem
247 agency homepages have been identified across 200+ NZ government agencies but none have automated page archiving configured. Raw HTML and extracted text need to be captured for provenance.

## Scope
- Compile full list of agency homepage URLs from registry and readiness matrix (247 homepages)
- Validate each URL is reachable (HTTP 200)
- Define per-agency website page contracts (crawl depth, page types, update frequency)
- Run initial capture for all 247 homepages
- Extract text using trafilatura for normalized content
- Set up scheduled weekly website capture

## Technical Approach
- Use `httpx` with retry/backoff for page fetching
- Store raw HTML with HTTP response headers
- Use `trafilatura` for text extraction
- Respect robots.txt and set polite crawl delays
- Store under `historical_archive_raw/website/` and `historical_archive_normalized/website/`

## Acceptance Criteria
- All 247 agency homepages captured with raw HTML and extracted text
- Per-agency website page contracts defined and validated
- Website capture manifest generated with per-agency counts
- Scheduled weekly capture workflow is active and verified
