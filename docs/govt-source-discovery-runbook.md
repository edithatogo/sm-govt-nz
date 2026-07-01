# Government Source Discovery and Archive Onboarding

For local Windows execution, prefer `.\scripts\dev.ps1 ...` or `uv run --python 3.14 ...` rather than bare `python`.

This repo now treats government public-source mapping as a repeatable pipeline:

1. `registry/government_directory.json` remains the canonical known agency and social-account inventory.
2. `config/govt_source_discovery.json` defines discovery paths, platform feasibility, archive status, auth posture, and preferred access methods.
3. `scripts/discover_govt_source_candidates.py` generates:
   - `conductor/govt_source_candidate_report.json`
   - `conductor/govt_source_candidate_summary.md`
   - `conductor/govt_archive_source_manifest.json`
4. `.github/workflows/govt_source_discovery.yml` runs the discovery daily and can also be run manually.

## What Is Mapped

The discovery report includes:

- every known registry social account, preserving platform, handle, URL, source status, account classification, and syndication classification where present;
- each official agency website as a public website archive candidate;
- known registry-backed social profiles, which are promoted into the archive manifest when they meet the automatic confidence and trust checks;
- common RSS/news/media/subscribe/newsletter path seeds for every agency website;
- optional bounded homepage probes for RSS/Atom alternates, newsletter/subscribe links, and social profile links.

The summary file is intentionally compact. The JSON report is the exhaustive review surface.

## Archive Feasibility

Archive onboarding is prioritized by feasibility:

- `ready`: public RSS, public website pages, and Bluesky where a direct public protocol is available.
- `candidate`: YouTube, newsletters, and other sources that need stable IDs, API access, or explicit ingress configuration.
- `manual_seed`: LinkedIn and similar platforms where approved API access, account-owner export, or bounded user-authorized capture is required.
- `degraded`: X/Twitter and other sources where account-owner export or public archive sources are preferred over live web capture.
- `blocked`: sources that should not be archived until legal, authentication, or technical prerequisites are resolved.

## Manual Source Registration

Use `.github/workflows/register_archive_source.yml` to add or update one archive source in `conductor/govt_archive_source_manifest.json`.

Minimum useful inputs:

- `source_id`
- `agency_id`
- `source_type`
- `platform`
- `url`
- `feasibility`
- `archive_status`
- `access_method`
- `auth`

The workflow calls `scripts/register_archive_source.py`, which upserts by `source_id` or by `(agency_id, platform, url)`.


## Feedback Learning

Review decisions can be fed back into discovery with `scripts/record_source_discovery_feedback.py`. The script writes to the path configured at `heuristics.learning_file`, normally `conductor/govt_source_discovery_learning.json`.

Daily discovery reads that learning file when scoring candidates. `accepted`, `approved`, `confirmed`, `official`, and `true_positive` decisions raise confidence; `rejected`, `false_positive`, `unofficial`, `exclude`, and `excluded` decisions lower confidence; `needs_review` leaves the candidate visible but slightly de-prioritized. Configured `official_account_terms` and `negative_account_terms` are also applied to the URL, account text, link text, link title, agency name, and website surface.

These signals change review priority and trust metadata only. They do not auto-register risky sources, publish archives, or override platform archive policy.

## Manual/API Onboarding

Use `.github/workflows/manual_seed_onboarding.yml` or `scripts/build_manual_seed_onboarding_report.py` to build `conductor/manual_seed_onboarding_report.json` for Facebook, Instagram, Threads, LinkedIn, X, and newsletters. This report is an onboarding queue, not a capture result.

For each source it records the accepted access methods, required authorization, candidate seed file paths, and the platform-specific no-scraping boundary. A source remains `needs_authorized_seed_or_api` until an approved API route, account-owner export, lawful public archive input, or operator-authorized seed JSON is available under `manual_archive_seeds/<platform>/<source_id>.json` or `manual_archive_seeds/<platform>/<agency_id>.json`.

The workflow also writes `conductor/manual_seed_onboarding_summary.md`, which is the compact remainder map for the manual/API queue. Use that summary when you need the current group counts at a glance and the JSON report when you need the per-source detail.

Run archive capture for these platforms only after the report shows `seed_present` or after a separately approved API adapter has been implemented. Missing seeds are reported as `manual_seed_missing`; the runner must not silently treat Meta, LinkedIn, or X as live-capturable.
## Archive Invocation

Use `.github/workflows/archive_registered_sources.yml` to select registered sources by platform or agency.

Current capture support:

- `website_page` sources are captured through bounded public HTML fetches.
- `rss_feed` sources are captured through `feedparser` when discovered feed URLs are registered.
- `bluesky` sources are captured through the public Bluesky author feed API.
- `youtube` sources resolve channel IDs from `/channel/`, `channel_id`, or public channel pages and capture public channel RSS feeds without credentials.
- Registry-backed `social_profile` sources are promoted automatically into the manifest when they are official and active; they are then processed by the platform-specific archive adapters below.
- `threads` sources are selected by the scheduled Threads archive workflow, but
  live public profile capture is disabled by default and only runs when
  `THREADS_API_CAPTURE_ENABLED=true` is deliberately configured after Meta
  approval for the required public-profile permission. If a matching
  operator-authorized seed exists under `manual_archive_seeds/threads/`, the
  runner archives that seed without requiring live API capture.
- `facebook`, `instagram`, `linkedin`, `newsletter`, `threads`, and `x` sources can be captured from operator-authorized manual seed JSON files under `manual_archive_seeds/<platform>/<source_id>.json` or `manual_archive_seeds/<platform>/<agency_id>.json`.
- platform sources without a seed file are reported as `manual_seed_missing`, not as successfully captured.

Archive failure triage is generated from dedicated platform reports with
`scripts/build_archive_failure_triage_report.py`. Apply conservative manifest
status updates with `scripts/apply_archive_failure_triage.py`; this degrades
malformed/stale YouTube URLs and blocked or stale website endpoints while
leaving valid-but-empty YouTube channels and transient website timeouts in the
monitored capture set.

Manual seed files contain a JSON object with `posts` or a bare list of post objects. Each post needs `url`, `created_at`, and `text`; `post_id`, `media`, `account`, and `canonical_url` are optional. This keeps the manifest exhaustive without overstating which sources are already captured.

For Threads, place authorized exports at either:

- `manual_archive_seeds/threads/<source_id>.json`
- `manual_archive_seeds/threads/<agency_id>.json`

For the currently registered Threads sources, the source-specific filenames are:

- `manual_archive_seeds/threads/nz-police-threads-newzealandpolice.json`
- `manual_archive_seeds/threads/nzte-threads-nzte.json`
- `manual_archive_seeds/threads/wellington-city-libraries-threads-wcl-library.json`

Use `manual_archive_seeds/threads/README.template.json` as the JSON shape.
The Threads-specific readiness queue is generated by
`scripts/build_threads_seed_readiness_report.py` and written to
`conductor/threads_seed_readiness_report.json` plus
`conductor/threads_seed_readiness_summary.md`.

Non-dry-run archive workflow runs build the archive compaction manifest and bundle the corpus with `scripts/publish_archives.py`. Set `publish=true` and choose `publication_target=all`, `huggingface`, or `zenodo` to publish through configured repository secrets; otherwise the workflow uploads a GitHub Actions artifact only.

For broad `all_feasible` review or interactive testing, use the workflow
batching controls instead of letting one run attempt every registered source:

- `limit_sources`: maximum selected sources to process; `0` means all selected sources.
- `offset_sources`: number of selected sources to skip before processing.
- `fetch_timeout`: per-source network fetch timeout in seconds.

The workflow also has a 45 minute job timeout so a small number of slow feeds,
web pages, or protocol endpoints cannot leave the archive job running
indefinitely. Scheduled runs still default to the full selected set.

Publication workflows are guarded to one external release per UTC month. The
release version is generated as `YYYY-MM`. If
`conductor/archive_publication_status.json` already records a successful
publication for that release version, later publish-enabled runs in the same
month still build the corpus and upload the GitHub Actions artifact, but they
do not push another Hugging Face, Zenodo, or OSF release.

Canonical publication status is reserved for external publication state. Plain
artifact-only runs write `dist/archive_publication_status_artifact.json`, and
same-month publish skips write `dist/archive_publication_status_skipped.json`.
They must not replace `conductor/archive_publication_status.json`. The archive
workflows call `scripts/validate_archive_publication_status.py` before bundling
to catch malformed canonical status files before they can affect publication
guard behavior.

## Daily Search Operation

The daily workflow:

1. checks out the repo;
2. runs `scripts/discover_govt_source_candidates.py --probe-homepages`;
3. commits the discovery report, summary, and archive manifest if anything changed.

Manual runs can disable homepage probing or limit `max_agencies` for a bounded test.

## Next Adapter Priorities

1. Run YouTube capture in dry-run, then live mode, and review unresolved channel IDs for manual correction.
2. Add manual seed files for high-value LinkedIn, Meta, X, and newsletter sources where exports or bounded captures are available.
3. Newsletter ingress manifests modelled on the Courts NZ email ingress.
4. Keep Threads on the explicit seed/API path unless approved public API access is restored.
5. Source-specific adapters for any platform where public, stable, policy-compliant APIs become available.

## Current Coverage Snapshot

- Automated archive lanes: RSS, JSON Feed, website pages, Bluesky, YouTube, and registry-backed official social profiles.
- Awaiting manual/API inputs: Facebook, Instagram, LinkedIn, Threads, X, and newsletters.
- Threads registered sources currently stay in `manual_seed_missing` until an authorized seed or approved API access appears.
