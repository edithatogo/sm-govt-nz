# Plan - Courts of New Zealand Multi-Source Archive and Dataset Pipeline

## Phase 1: Source Inventory and Access Contracts
- [x] Task: Record official Courts of New Zealand source surfaces in repo config: Bluesky, LinkedIn, inactive X archive, website/RSS, and judgments email subscription.
- [x] Task: Discover all Courts of New Zealand RSS feed URLs by parsing page-level RSS links and site sections for judgments, announcements, speeches, reports, and daily lists.
- [x] Task: Confirm LinkedIn access method and constraints: official API if admin access exists, otherwise user-authorized browser export/capture or no-code manual seed.
- [x] Task: Confirm historical X archive method for pre-23-March-2025 `@courtsofnz` posts: public X archive, Internet Archive/CDX, browser capture, or another lawful export path.
- [x] Task: Define source health status values: healthy, degraded, auth_required, rate_limited, blocked, and unavailable.
- [x] Task: Document one adapter contract per source, including input credentials, output paths, dedupe keys, rate-limit handling, archive-only guarantee, and phase review checklist.

## Phase 2: Archive Schema and Deduplication
- [x] Task: Extend archive schema to include `source_platform`, `source_account`, `source_kind`, `captured_at`, `raw_path`, `canonical_url`, `content_hash`, and `cross_source_ids`.
- [x] Task: Add source-specific raw archive directories under `historical_archive_raw/<source>/<yyyy-mm>/`.
- [x] Task: Add normalized monthly shards under `historical_archive_normalized/<source>/<yyyy-mm>.jsonl`.
- [x] Task: Implement canonical dedupe across Bluesky, LinkedIn, RSS, email, and website pages using canonical URL plus text/media hash fallback.
- [ ] Task: Ensure archive-only backfill state cannot advance `conductor/state.json` for outbound syndication.

## Phase 3: Historical Backfills
- [ ] Task: Re-run Bluesky historical archive as an idempotent backfill and write a gap report.
- [ ] Task: Archive inactive historical X posts for `@courtsofnz` and write a provenance/access report.
- [ ] Task: Archive historical LinkedIn posts and write a provenance/access report.
- [ ] Task: Archive available RSS histories and write per-feed reports.
- [ ] Task: Keep all historical backfills out of live syndication targets.

## Phase 4: Ongoing Capture Pipeline
- [ ] Task: Add a scheduled archive-only workflow that runs in parallel with `Syndicate`.
- [ ] Task: Capture current Bluesky feed into both raw and normalized archives.
- [ ] Task: Capture LinkedIn posts through the approved access method.
- [ ] Task: Capture RSS feed entries with `feedparser`.
- [ ] Task: Capture source website pages linked from posts/feed/email when they provide canonical judgments, speeches, reports, or announcements.
- [ ] Task: Commit archive state and source health reports back to GitHub.

## Phase 5: Judgments Email Subscription Ingress
- [ ] Task: Use Cloudflare Email Routing Worker as the default email ingress bridge because it has a free routing path and enough free Worker request capacity for low-volume notification capture.
- [ ] Task: Keep Mailgun inbound parse as a fallback only if Cloudflare parsing/routing is insufficient and a trial or paid plan is acceptable.
- [ ] Task: Keep scheduled mailbox polling through Gmail or IMAP as the final fallback if webhook-style inbound delivery is unavailable.
- [ ] Task: Create a dedicated subscription address for Courts of NZ judgments of public interest notifications.
- [ ] Task: Store raw email payloads under `historical_archive_raw/email/<yyyy-mm>/`.
- [ ] Task: Normalize email subject/body/link records into the shared archive schema.
- [ ] Task: Trigger GitHub Actions with `repository_dispatch` or a scheduled polling workflow after email receipt.

## Phase 6: Hugging Face and Zenodo Corpus Publication
- [ ] Task: Define the Hugging Face dataset name, license/readme, citation, and provenance statement.
- [ ] Task: Define the Zenodo deposition metadata, communities if any, citation fields, DOI/versioning policy, and provenance statement.
- [ ] Task: Add `HF_TOKEN`, `HF_DATASET_REPO_ID`, `ZENODO_TOKEN`, and `ZENODO_DEPOSIT_ENDPOINT` setup requirements to the setup guide and secret schema.
- [ ] Task: Publish normalized JSONL and Parquet shards to Hugging Face Datasets.
- [ ] Task: Publish citable release snapshots to Zenodo from the same normalized archive artifacts.
- [ ] Task: Publish raw-source bundles separately or as a gated/manual artifact if size or platform terms require it.
- [ ] Task: Add dataset manifests with checksums, source coverage, date ranges, and known gaps.

## Phase 7: Operational Optimizations
- [ ] Task: Add source-health dashboard output to Pages.
- [ ] Task: Add no-op scheduled-run monitoring to confirm no duplicate posts are generated.
- [ ] Task: Add monthly compaction so Git commits stay small while Hugging Face receives dataset-friendly shards.
- [ ] Task: Add Buffer API key rotation reminder before the current key expiry on 12 July 2026.
- [ ] Task: Add failure isolation so one blocked source does not stop other archive sources or live Bluesky-to-X mirroring.
- [ ] Task: Commit after each completed implementation task and run a review after each phase before starting the next phase.

## Deferred Tracks: Additional Syndication Accounts
- [ ] Task: Create one separate conductor track per future outbound platform account after the archive pipeline is stable.
- [ ] Task: Require each future syndication track to define posting contracts, source-to-target mapping, duplicate prevention, secret requirements, rate limits, rollback steps, and review gates before implementation.
