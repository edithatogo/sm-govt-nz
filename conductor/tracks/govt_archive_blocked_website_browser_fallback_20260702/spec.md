# Specification: NZ Government Archive - blocked website browser fallback capture

## Overview
This track addresses public website pages that remain blocked after ordinary HTTP capture. It adds a conservative Playwright/browser fallback for public rendered pages, with raw evidence snapshots and clear anti-bypass boundaries. It is a larger follow-up project because browser capture adds runtime, dependencies, and failure modes.

## Functional Requirements
- Define which website failure states are eligible for browser fallback and which remain retired or blocked.
- Implement public rendered capture for eligible URLs using a browser workflow without login, CAPTCHA solving, proxies, or credential bypass.
- Store raw HTML, screenshots where appropriate, normalized extracted text, and per-source diagnostics under canonical archive paths.
- Shard and limit browser runs so GitHub Actions remains reliable and polite.
- Report fallback success, blocked, timeout, not found, and no-visible-content states distinctly.

## Non-Functional Requirements
- Prefer public, lawful, keyless capture paths unless the track explicitly documents an opt-in credentialed path.
- Preserve existing monthly external publication guards for Hugging Face and Zenodo.
- Keep machine-readable reports deterministic so automation can act without manual decisions.
- Avoid deleting source registrations solely because a source is blocked, missing input, or temporarily unavailable.

## Acceptance Criteria
- Browser fallback runs only for eligible public website sources and is disabled or bounded by workflow inputs.
- Captured evidence is written to raw and normalized archive paths without duplicating existing HTTP records.
- Persistent anti-bot or CAPTCHA outcomes are recorded, not bypassed.
- Tests cover eligibility classification and fixture-based extraction.
- Scheduled or manual workflows can run browser fallback shards and feed monthly publication.

## Out of Scope
- Automated login to government websites.
- CAPTCHA solving, stealth bypass, proxy rotation, or credential harvesting.
- Replacing simple HTTP capture for sources that already archive reliably.

