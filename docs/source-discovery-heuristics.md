# Government Source Discovery Heuristics

The repository runs a daily `Government Source Discovery` workflow to identify
new NZ government public-source candidates and open or update a review issue when
something new appears.

## What the discovery pass looks for

The discovery pipeline treats these surfaces as first-class candidates:

- RSS and Atom feeds
- JSON Feed
- WebSub hubs
- Bluesky public profiles and posts
- ActivityPub and WebFinger endpoints
- Public APIs and OpenAPI documents
- Microformats such as `h-feed` and `h-entry`
- Bounded public website pages linked from official source surfaces

## Heuristic bias

The discovery config prefers official NZ government and public-sector domains,
including:

- `.govt.nz`
- `.parliament.nz`
- `.ac.nz`
- `.mil.nz`
- `.cri.nz`

It also boosts account text that looks like a real public body, for example:

- `government`
- `govt`
- `public`
- `board`
- `crown`
- `department`
- `service`
- `library`
- `parliament`
- `ministry`
- `commission`
- `agency`
- `council`
- `authority`

## Negative filters

The discovery workflow de-prioritizes or rejects obvious false positives such as:

- fan accounts
- parody accounts
- unofficial mirrors
- archive-only copies
- unrelated accounts

## Review workflow

The scheduled discovery job:

1. Runs on a daily cron.
2. Probes a bounded set of official homepages and common source paths.
3. Writes the full candidate report to `conductor/govt_source_candidate_report.json`.
4. Builds or updates a GitHub issue labeled `source-discovery` and `needs-review`
   when reviewable candidates exist.
5. Uses the learning file at `conductor/govt_source_discovery_learning.json` to
   record accepted or rejected examples so the heuristics can be tightened over
   time.

## Operational rule

False positives are acceptable if they help surface real official sources faster.
The review issue exists to tighten precision after discovery, not to block
collection of a promising candidate.
