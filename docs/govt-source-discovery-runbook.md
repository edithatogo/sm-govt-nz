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

## Archive Invocation

Use `.github/workflows/archive_registered_sources.yml` to select registered sources by platform or agency.

Current capture support:

- `website_page` sources are captured through bounded public HTML fetches.
- `rss_feed` sources are captured through `feedparser` when discovered feed URLs are registered.
- `bluesky` sources are captured through the public Bluesky author feed API.
- `facebook`, `instagram`, `linkedin`, `newsletter`, `threads`, `x`, and `youtube` sources can be captured from operator-authorized manual seed JSON files under `manual_archive_seeds/<platform>/<source_id>.json` or `manual_archive_seeds/<platform>/<agency_id>.json`.
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

1. Add manual seed files for high-value LinkedIn, Meta, X, YouTube, and newsletter sources where exports or bounded captures are available.
2. YouTube handle-to-channel-id resolver and channel RSS capture.
3. Newsletter ingress manifests modelled on the Courts NZ email ingress.
4. Meta platform live capture only through approved Graph/Threads API access or account-owner export.
5. Source-specific adapters for any platform where public, stable, policy-compliant APIs become available.
