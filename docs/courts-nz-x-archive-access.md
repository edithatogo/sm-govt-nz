# Courts of New Zealand X Archive Access Contract

## Decision
The historical X backfill should use Internet Archive CDX captures over the
legacy `twitter.com/CourtsofNZ/status/*` URL pattern as the primary public
source. This should be treated as a partial, provenance-heavy archive path, not
as a complete replacement for an account-owner export.

## Rationale
The Courts of New Zealand notification page states that the X account is no
longer active and that posts before 23 March 2025 remain available on X. X's
own help pages describe an account-owner data archive export, but that requires
control of the source X account and is not available to this project unless the
Courts provides it.

Internet Archive CDX is the best non-owner first pass because it exposes
structured snapshot metadata. A live probe on 12 June 2026 found substantially
more captures for the legacy Twitter host than for the X host:

- `twitter.com/CourtsofNZ/status/*`: 937 status captures
- `x.com/CourtsofNZ/status/*`: 18 status captures

## Approved Access Order
1. Use an account-owner X data archive if Courts of New Zealand provides one.
2. Use Internet Archive CDX over `twitter.com/CourtsofNZ/status/*` for the
   first public historical backfill.
3. Use Internet Archive CDX over `x.com/CourtsofNZ/status/*` as supplementary
   coverage.
4. Use bounded user-authorized browser capture only for gaps that cannot be
   resolved through archive/export sources.

## Guardrails
- X records are archive-only historical inputs in this track.
- X records must never enter any live outbound posting queue.
- Each captured record must keep snapshot timestamp, original URL, canonical
  status URL, digest when available, extraction method, and capture source.
- CDX records may contain duplicate captures of the same status and must be
  deduplicated by tweet ID plus content hash.
- Browser capture must be bounded, operator-authorized, and produce a
  provenance report.

## References
- Courts of New Zealand notification page:
  https://www.courtsofnz.govt.nz/home/receiving-notifications-of-judgments-of-public-interest-and-judicial-announcements
- Internet Archive Wayback API documentation:
  https://archive.org/help/wayback_api.php
- X data archive help:
  https://help.x.com/en/managing-your-account/accessing-your-x-data
