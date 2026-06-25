# Government Source Discovery and Archive Onboarding

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
- common RSS/news/media/subscribe/newsletter path seeds for every agency website;
- optional bounded homepage probes for RSS/Atom alternates, newsletter/subscribe links, and social profile links.

The summary file is intentionally compact. The JSON report is the exhaustive review surface.

## Archive Feasibility

Archive onboarding is prioritized by feasibility:

- `ready`: public RSS, public website pages, and Bluesky where a direct public protocol is available.
- `candidate`: YouTube, Facebook, Instagram, Threads, newsletters, and other sources that need stable IDs, API access, or explicit ingress configuration.
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

Use `.github/workflows/manual_seed_onboarding.yml` or `scripts/build_manual_seed_onboarding_report.py` to build `conductor/manual_seed_onboarding_report.json` for Facebook, Instagram, LinkedIn, and X. This report is an onboarding queue, not a capture result.

For each source it records the accepted access methods, required authorization, candidate seed file paths, and the platform-specific no-scraping boundary. A source remains `needs_authorized_seed_or_api` until an approved API route, account-owner export, lawful public archive input, or operator-authorized seed JSON is available under `manual_archive_seeds/<platform>/<source_id>.json` or `manual_archive_seeds/<platform>/<agency_id>.json`.

Run archive capture for these platforms only after the report shows `seed_present` or after a separately approved API adapter has been implemented. Missing seeds are reported as `manual_seed_missing`; the runner must not silently treat Meta, LinkedIn, or X as live-capturable.
## Archive Invocation

Use `.github/workflows/archive_registered_sources.yml` to select registered sources by platform or agency.

Current capture support:

- `website_page` sources are captured through bounded public HTML fetches.
- `rss_feed` sources are captured through `feedparser` when discovered feed URLs are registered.
- `bluesky` sources are captured through the public Bluesky author feed API.
- `youtube` sources resolve channel IDs from `/channel/`, `channel_id`, or public channel pages and capture public channel RSS feeds without credentials.
- `facebook`, `instagram`, `linkedin`, `newsletter`, `threads`, and `x` sources can be captured from operator-authorized manual seed JSON files under `manual_archive_seeds/<platform>/<source_id>.json` or `manual_archive_seeds/<platform>/<agency_id>.json`.
- platform sources without a seed file are reported as `manual_seed_missing`, not as successfully captured.

Manual seed files contain a JSON object with `posts` or a bare list of post objects. Each post needs `url`, `created_at`, and `text`; `post_id`, `media`, `account`, and `canonical_url` are optional. This keeps the manifest exhaustive without overstating which sources are already captured.

Non-dry-run archive workflow runs build the archive compaction manifest and bundle the corpus with `scripts/publish_archives.py`. Set `publish=true` and choose `publication_target=all`, `huggingface`, or `zenodo` to publish through configured repository secrets; otherwise the workflow uploads a GitHub Actions artifact only.

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
4. Meta platform live capture only through approved Graph/Threads API access or account-owner export.
5. Source-specific adapters for any platform where public, stable, policy-compliant APIs become available.
