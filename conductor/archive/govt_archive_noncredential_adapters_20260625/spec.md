# Spec - NZ Government Archive - maximise non-credential source capture

## Problem
Many government social media platforms require account creation, app review, or platform credentials before mirroring can be automated. The system should still maximize archival coverage from public sources that do not require those credentials.

## Scope
Implement a source-type roadmap and adapter backlog for websites, RSS/Atom, sitemaps, YouTube channel RSS, Bluesky public API records, public newsletter pages, and agency media-release pages.

## Required Outputs
- Adapter-feasibility matrix ranked by public value and credential burden.
- Per-adapter dry-run/live workflow requirements.
- Library evaluation notes for `feedparser`, `httpx`, `trafilatura` or equivalent article extraction, YouTube RSS, and AT Protocol public reads.
- Source health grouping by platform and failure class.

## Acceptance Criteria
- All non-credential source types have explicit dry-run and live archive workflows planned.
- Source failures are grouped by fixable class rather than undifferentiated failures.
- Public source capture is maximized without requiring new platform accounts.
