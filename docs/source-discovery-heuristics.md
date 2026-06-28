# Source Discovery Heuristics

The source-discovery pipeline identifies candidate public communication sources
for the New Zealand government social-media corpus. Discovery is deliberately
conservative: candidates are surfaced for review before being treated as
authoritative archive sources unless they come from the registry or an accepted
per-agency config.

## Source classes

- `rss`: RSS and Atom feeds discovered from `link rel=alternate`, common feed
  paths, or visible feed links.
- `json_feed`: JSON Feed links, usually `application/feed+json` or `feed.json`.
- `websub`: `link rel=hub` endpoints that can support realtime feed delivery.
- `bluesky`: public AT Protocol profiles from registry records, homepage links,
  or targeted search seeds.
- `activitypub`: ActivityPub/Fediverse profiles, WebFinger hints, Mastodon links,
  or `application/activity+json` alternates.
- `api`: public API/OpenAPI/Swagger/developer links that may expose stable public
  communications records.
- `microformat`: pages containing or advertising microformats such as `h-feed`
  and `h-entry`.
- `newsletter`: subscription and email update pages that need explicit ingress
  setup before automated archiving.

## Confidence signals

Positive signals:

- source is already in the government registry;
- URL is on a high-trust domain such as `.govt.nz`, `.parliament.nz`, `.mil.nz`,
  `.cri.nz`, or `.ac.nz`;
- account/page text contains official terms such as `ministry`, `commission`,
  `agency`, `council`, `department`, or `authority`;
- historical discovery-learning records mark the source as accepted.

Negative signals:

- terms such as `fan`, `parody`, `unofficial`, `archive only`, or `not affiliated`;
- historical discovery-learning records mark the source as rejected;
- search-only seeds without homepage or registry evidence.

## Definite feed onboarding rules

Feeds can be moved directly into archive configs when they are discovered from
an official government homepage as `link rel=alternate` with RSS or Atom MIME
metadata, or when the visible link is an explicit feed endpoint such as
`atom.xml`, `rss.xml`, `/home/changes`, `/home/rss`, `/homerss`, `/feed/`,
`/feed/rss2`, `/feed/atom`, or `/feed/news`.

Do not auto-onboard links that merely contain matching substrings. Known noisy
patterns include `/feedback`, explanatory pages such as `what-is-rss`, WordPress
REST/oEmbed URLs under `wp-json`, LinkedIn share URLs containing `/feed/`, and
topic pages where `feedlot` or similar prose is part of the path.

Public API candidates must match API as a path segment or an explicit
OpenAPI/Swagger/developer surface. Substrings inside agency names or places,
such as `Napier` or `rapid`, are not API evidence.

JSON Feed candidates require `application/feed+json`, an explicit
`/feed.json`, or visible `JSON Feed` text. Generic JSON, WordPress REST, and
oEmbed discovery links are not treated as JSON feeds.

## Realtime versus scheduled capture

- RSS/Atom/JSON Feed polling remains the fallback and reconciliation mechanism.
- WebSub is preferred where a feed advertises a hub, but WebSub delivery is not
  assumed to be complete.
- Bluesky firehose ingestion is preferred for realtime capture, but daily
  Bluesky reconciliation remains required for cursor gaps and bridge downtime.
- API and microformat sources require review before automated ingestion.

## Issue workflow

The `Government Source Discovery` workflow runs daily and on manual dispatch.
It writes:

- `conductor/govt_source_candidate_report.json`
- `conductor/govt_source_candidate_summary.md`
- `conductor/govt_archive_source_manifest.json`

When reviewable candidates are detected, the workflow creates or updates one
GitHub issue labelled `source-discovery` and `needs-review`.
