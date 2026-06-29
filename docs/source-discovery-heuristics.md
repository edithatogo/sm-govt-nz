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
- Threads public profiles on `threads.net` and `threads.com`
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

## Threads-specific review rule

Only register a Threads account for live archival when it is clearly tied to a
central or local NZ government body, such as an official website link, an
existing registry social-profile match, or a profile description that names the
public body. Current confirmed registered Threads sources are New Zealand
Police, New Zealand Trade and Enterprise, and Wellington City Libraries.

The archive runner no longer requires numeric Threads user IDs before attempting
capture. It tries official profile-post lookup by handle first. If the scheduled
workflow reports `threads_permission_error`, treat that as an upstream Meta
app/token blocker, not as a missing-source-registration problem.
