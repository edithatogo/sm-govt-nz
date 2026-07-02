# Spec - NZ Government Archive - gap prioritization and seed intake hardening

## Problem

The archive system captures keyless/public sources, but residual gaps are reported with low-level statuses that do not clearly distinguish between fixable URL/adapter work, existing manual-seed intake gaps, operator/API access needs, and larger browser/access projects.

## Scope

Classify current archive gaps into implementation priorities, surface the classification as machine-readable reports, document manual seed intake for Threads, LinkedIn, and newsletters, and harden the most obvious URL-level YouTube failure pattern.

## Requirements

- Preserve lawful public/keyless capture as the default path.
- Treat `manual_seed_missing` as a tracked zero-input state, not a workflow failure.
- Generate deterministic gap maps from archive reports.
- Add automated gap-map generation to capture workflows.
- Document seed file shape and directory conventions for operator-authorized seed inputs.
- Do not implement logged-in capture, cookie extraction, private GraphQL capture, CAPTCHA bypass, or paid/approved API use in this track.

## Acceptance Criteria

- Archive reports can be summarized by priority class.
- Website and YouTube scheduled capture workflows commit gap-map artifacts.
- Registered-source capture commits a gap-map artifact after non-dry-run captures.
- LinkedIn and newsletter seed templates exist alongside the existing Threads seed convention.
- YouTube handles with accidental spaces in `@handle` URLs are normalized before fetch.
- Tests cover gap-map classification, workflow hooks, and YouTube handle normalization.

## Implementation Evidence

- Implementation commit: `87d9842`.
- Generated gap map: `conductor/archive_gap_map.json`.
