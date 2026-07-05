# Specification: NZ Government Archive - Threads personal-account archive path

## Overview

The archive system already supports Threads API capture behind an explicit gate. This track narrows the Threads documentation and operator guidance to the archive-only, personal-account path that can be enabled now, while deferring broader Meta platform work such as Instagram and Facebook to later tracks.

## Functional Requirements

- Describe Threads as archive-only, not mirroring.
- Document that a personal Threads account token can be used when `THREADS_API_CAPTURE_ENABLED=true` is set.
- Keep manual seed exports as the fallback archive path when API access is not enabled.
- Leave Instagram and Facebook unchanged and deferred.
- Keep the workflow and operator guidance read-only until an archive action is explicitly run.

## Non-Goals

- Posting to Threads.
- Launching Instagram or Facebook capture from a personal account.
- Changing the broader Meta access strategy beyond Threads.

## Acceptance Criteria

- Threads seed guidance documents the personal-account archive path.
- The scheduled Threads workflow explains the personal-account gate and archive-only behavior.
- Tests cover the updated Threads guidance wording.
- The wider Meta platforms remain deferred.

