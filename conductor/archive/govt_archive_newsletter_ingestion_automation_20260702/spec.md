# Specification: NZ Government Archive - newsletter and email ingestion automation

## Overview
This track builds on the manual seed lane to make newsletter and email capture operational. It covers inbound payload normalization, seed backfill, source status reporting, and optional mailbox/route integration boundaries, while keeping credentials and external mailbox setup separate from repository implementation.

## Functional Requirements
- Normalize newsletter/email payloads from seed files and future inbound bridge payloads into canonical archive records.
- Document supported inputs such as .eml exports, JSON payloads, HTML bodies, text bodies, sender metadata, and subscription URLs.
- Add deterministic source matching between registered newsletter sources and incoming payloads.
- Produce reports for missing subscriptions, missing payloads, invalid payloads, and archived messages.
- Keep inbound provider configuration optional and disabled unless the required secrets or external routes exist.

## Non-Functional Requirements
- Prefer public, lawful, keyless capture paths unless the track explicitly documents an opt-in credentialed path.
- Preserve existing monthly external publication guards for Hugging Face and Zenodo.
- Keep machine-readable reports deterministic so automation can act without manual decisions.
- Avoid deleting source registrations solely because a source is blocked, missing input, or temporarily unavailable.

## Acceptance Criteria
- Newsletter seed and inbound payload parser paths are tested with fixtures.
- Registered newsletter sources can transition from manual_seed_missing to archived when payloads exist.
- Reports distinguish source subscription gaps from parser failures.
- No real mailbox credentials or private email content are required for CI.
- Monthly dataset publication includes newsletter records when present.

## Out of Scope
- Setting up paid inbound email services without explicit approval.
- Subscribing to every newsletter manually.
- Capturing personal mailbox content unrelated to registered public sources.

