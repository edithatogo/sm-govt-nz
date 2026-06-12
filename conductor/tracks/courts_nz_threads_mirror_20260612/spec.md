# Specification - Courts of New Zealand Threads Mirror Account

## Overview
Create and configure a dedicated Threads mirror account for Courts of New
Zealand content. Threads posting is a separate outbound track and must not reuse
personal Instagram/Threads identity or LinkedIn credentials.

## Requirements
1. Account identity:
   - Use an unofficial mirror name based on `Mirror: Courts of New Zealand`.
   - Do not post under Dylan Mordaunt, `edithatogo`, or any personal identity.
   - Use `edithatogo@gmail.com` for account administration where practical.
   - Include source attribution to `courtsofnz.bsky.social`.
2. Posting route:
   - Prefer official Meta/Threads API routes if free and suitable for the
     mirror account.
   - Use Buffer only if it preserves account identity, attribution, and
     duplicate-prevention guarantees.
   - Do not use browser automation for unattended posting unless a later review
     explicitly approves that risk.
3. Guardrails:
   - No live posting until account identity, credentials, dry run, and review
     gates are complete.
   - Historical records must not be posted as a backlog.
   - LinkedIn remains source-only and must not influence this posting track.

## Acceptance Criteria
- The Threads mirror account exists with archived profile evidence.
- Required credentials and platform limits are documented without storing
  secrets in Git.
- A dry-run plan demonstrates one source post mapping to one Threads post or
  thread.
- A controlled live test posts only new content and records the resulting URL.
