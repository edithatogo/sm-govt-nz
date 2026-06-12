# Plan - Courts of New Zealand Multi-Source Archive and Dataset Pipeline

## Phase 1: Source Inventory and Access Contracts
- [ ] Task: Record official Courts of New Zealand source surfaces in repo config: Bluesky, LinkedIn, inactive X archive, website/RSS, and judgments email subscription.
- [ ] Task: Discover all Courts of New Zealand RSS feed URLs by parsing page-level RSS links and site sections for judgments, announcements, speeches, reports, and daily lists.
- [ ] Task: Confirm LinkedIn access method and constraints: official API if admin access exists, otherwise user-authorized browser export/capture or no-code manual seed.
- [ ] Task: Confirm historical X archive method for pre-23-March-2025 `@courtsofnz` posts: public X archive, Internet Archive/CDX, browser capture, or another lawful export path.
- [ ] Task: Define source health status values: healthy, degraded, auth_required, rate_limited, blocked, and unavailable.

## Phase 2: Archive Schema and Deduplication
- [ ] Task: Extend archive schema to include `source_platform`, `source_account`, `source_kind`, `captured_at`, `raw_path`, `canonical_url`, `content_hash`, and `cross_source_ids`.
- [ ] Task: Add source-specific raw archive directories under `historical_archive_raw/<source>/<yyyy-mm>/`.
- [ ] Task: Add normalized monthly shards under `historical_archive_normalized/<source>/<yyyy-mm>.jsonl`.
- [ ] Task: Implement canonical dedupe across Bluesky, LinkedIn, RSS, email, and website pages using canonical URL plus text/media hash fallback.
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
- [ ] Task: Choose email ingress bridge: Cloudflare Email Routing Worker, Mailgun inbound parse, or scheduled mailbox polling.
- [ ] Task: Create a dedicated subscription address for Courts of NZ judgments of public interest notifications.
- [ ] Task: Store raw email payloads under `historical_archive_raw/email/<yyyy-mm>/`.
- [ ] Task: Normalize email subject/body/link records into the shared archive schema.
- [ ] Task: Trigger GitHub Actions with `repository_dispatch` or a scheduled polling workflow after email receipt.

## Phase 6: Hugging Face Dataset Publication
- [ ] Task: Define the Hugging Face dataset name, license/readme, citation, and provenance statement.
- [ ] Task: Add `HF_TOKEN` and `HF_DATASET_REPO_ID` setup requirements to the setup guide and secret schema.
- [ ] Task: Publish normalized JSONL and Parquet shards to Hugging Face Datasets.
- [ ] Task: Publish raw-source bundles separately or as a gated/manual artifact if size or platform terms require it.
- [ ] Task: Add dataset manifests with checksums, source coverage, date ranges, and known gaps.

## Phase 7: Operational Optimizations
- [ ] Task: Add source-health dashboard output to Pages.
- [ ] Task: Add no-op scheduled-run monitoring to confirm no duplicate posts are generated.
- [ ] Task: Add monthly compaction so Git commits stay small while Hugging Face receives dataset-friendly shards.
- [ ] Task: Add Buffer API key rotation reminder before the current key expiry on 12 July 2026.
- [ ] Task: Add failure isolation so one blocked source does not stop other archive sources or live Bluesky-to-X mirroring.
