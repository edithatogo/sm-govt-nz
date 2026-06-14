# Setup Guide

This guide covers the platform accounts, GitHub secrets, and validation steps
needed to run the NZ Government Bluesky Syndicator and transparency dashboard.

## 1. GitHub Repository Setup

Enable GitHub Actions and Pages for the repository.

Required repository settings:

- Actions: enabled.
- Pages: GitHub Actions deployment source.
- Branch: `master` or `main`.
- Optional project routing: create a GitHub Project and set repository variables
  `PROJECT_NUMBER` and `PROJECT_OWNER`.

## 2. Current MVP Outbound Posting: Bluesky Mirror

The current MVP is scoped to mirroring Courts of New Zealand Bluesky posts to a
dedicated Bluesky mirror account before any additional platforms are enabled.
`config.json` enables only the `bluesky` target and sets
`max_posts_per_run` to `1` for the controlled launch period.

Historical backlog posting is also enabled for the Bluesky mirror. It is
bounded separately with `backlog_max_posts_per_run: 1`, ordered
`oldest_first`, and tracked in `conductor/bluesky_backlog_state.json` so it does
not rewind or interfere with live `conductor/state.json` processing.

Required GitHub secrets:

- `BLUESKY_MIRROR_HANDLE`
- `BLUESKY_MIRROR_APP_PASSWORD`

Local setup:

```powershell
python scripts/validate_secrets.py --mode syndicate --target bluesky
python scripts/bluesky_api_probe.py
python scripts/post_bluesky_backlog.py --dry-run
```

Generate the app password from the dedicated Bluesky mirror account. The probe
creates an authenticated session and prints only the handle/DID; it does not
publish content.

After adding both secrets, run the `Validate Syndication Secrets` workflow. It
checks the Bluesky credential path without posting.

## 3. Deferred X Posting: Buffer or Direct API

X posting is deferred while the Bluesky mirror MVP is implemented. When reopened,
the preferred X route is Buffer's official CLI because it may avoid direct X API
credits when Buffer's connected X channel supports automatic publishing.

Buffer secrets:

- `BUFFER_API_KEY`
- `BUFFER_X_CHANNEL_ID`

Direct X API posting through Tweepy remains available as a fallback, but it
requires X developer API credits.

Direct X secrets:

- `X_API_KEY`
- `X_API_SECRET`
- `X_ACCESS_TOKEN`
- `X_ACCESS_TOKEN_SECRET`

The X app must have write permissions and the access token must be regenerated
after write permissions are enabled. A browser-submitted post proves the account
can post manually, but it does not prove the unattended API workflow can post.

Validate the API path locally:

```powershell
python scripts/x_api_probe.py
python scripts/x_api_probe.py --write-probe
```

The write probe creates and immediately deletes a probe post. It requires X API
credits. A `402 Payment Required` response means the credentials work but the X
developer account needs usable credits or billing before scheduled syndication
can be enabled.

## 4. Additional Platform Targets

- Discord: `DISCORD_WEBHOOK_URL`
- Mastodon: `MASTODON_BASE_URL`, `MASTODON_ACCESS_TOKEN`
- Threads mirror: `THREADS_ACCESS_TOKEN`, `THREADS_USER_ID`
  (`THREADS_MIRROR_ACCOUNT_ID` remains accepted as a legacy local alias)
- Instagram mirror: `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_USER_ID`

LinkedIn is not an outbound posting target in the current roadmap. It is a
source/archive lane only, and no repository workflow should use a personal
LinkedIn profile or token to post.

### Bluesky Mirror Account

Create a dedicated account under the systematic mirror identity, administered
through `edithatogo@gmail.com` where practical. The expected handle pattern is
`mirnzcourts.bsky.social` unless a better available handle is selected during
account creation.

Bluesky supports a more complete historical mirror mode than Threads because
AT Protocol posts are repository records and the public source corpus can be
read through public AT Protocol APIs. Historical backfill still requires a
separate review gate because replayed records can appear as new activity to
followers even when the post text preserves original source attribution.

### Threads Mirror Account

Create a dedicated Threads account under the systematic mirror identity,
administered through `edithatogo@gmail.com` where practical. Do not use a
personal Instagram or Threads identity.

Prepared account:

- URL: `https://www.threads.com/@mirnzcourts`
- Handle: `mirnzcourts`
- Display name: `Mirror: Courts of New Zealand`
- Status: account/profile prepared, outbound posting disabled until the
  Bluesky backlog has completed or is explicitly paused.

The scheduled `Syndicate` workflow includes a Threads pipeline gate. It does not
post to Threads yet; it reports the configured Threads account and waits for the
Bluesky backlog to finish before the Threads API credential and posting adapter
work is enabled.

Threads can publish posts through the official Threads API using a two-step
container and publish flow. Use a long-lived Threads user token where practical;
Meta documents long-lived tokens as valid for 60 days and refreshable before
expiry. The current official API does not provide a true historical
import/backdate route for a mirror corpus. Treat Threads as ongoing-forward
mirroring by default. Any historical replay to Threads must be a separate
reviewed batch job because it would publish records as current Threads posts and
is subject to platform limits.

Non-posting validation:

```powershell
python scripts/validate_secrets.py --mode syndicate --target threads
python scripts/threads_api_probe.py
```

GitHub validation:

- Add `THREADS_ACCESS_TOKEN` and `THREADS_USER_ID` as repository secrets.
- Run the manual `Validate Threads` workflow. It validates secret shape and
  probes the Threads profile identity without publishing.

### Instagram Mirror Account

The Instagram account is prepared under the same Meta account/admin structure as
Threads. It remains disabled in `config.json` until the Threads launch is stable
and the Instagram API route validates.

Expected mirror profile:

- URL: `https://www.instagram.com/mirnzcourts/`
- Handle: `mirnzcourts`
- Status: account/profile prepared, outbound posting disabled.

Non-posting validation:

```powershell
python scripts/validate_secrets.py --mode syndicate --target instagram
python scripts/instagram_api_probe.py
```

GitHub validation:

- Add `INSTAGRAM_ACCESS_TOKEN` and `INSTAGRAM_USER_ID` as repository secrets.
- Run the manual `Validate Instagram` workflow. It validates secret shape and
  probes the Instagram profile identity without publishing.

Instagram publishing is a separate track from Threads. The same Meta account may
administer both, but Instagram needs its own user ID, permissions, token
validation, posting adapter, duplicate state, and launch review.

### Facebook Page Mirror

The Facebook Page mirror is not set up yet. Do not add Facebook Page secrets or
enable Facebook posting until the dedicated Page exists and the Facebook track
has completed the account-readiness phase.

## 5. Archive Publishing

For external archive publishing, configure:

- Zenodo: `ZENODO_TOKEN`, `ZENODO_DEPOSIT_ENDPOINT`
- Hugging Face: `HF_TOKEN`, `HF_DATASET_REPO_ID`

The Pages workflow builds a local archive bundle. Publishing to external archive
services is controlled by the publishing script and environment credentials.

## 6. Courts of New Zealand Multi-Source Archive

The Courts of New Zealand archive expansion is tracked in
`conductor/tracks/courts_nz_multisource_archive_20260612/`.
The source inventory and adapter contracts are defined in
`config/courts_nz_sources.json` and validated by `src/source_inventory.py`.

Planned source lanes:

- Bluesky: `courtsofnz.bsky.social` via public AT Protocol feed capture.
- LinkedIn: official Courts of New Zealand page, using an approved API/export or
  user-authorized capture path.
- Historical X: inactive `@courtsofnz` public archive, limited to posts before
  23 March 2025.
- RSS/website: Courts of New Zealand page-level RSS feeds and canonical website
  pages for judgments, announcements, speeches, reports, and daily lists.
- Email: judgments of public interest subscription messages.

GitHub does not provide a native inbound mailbox for repository workflows. To
capture subscription emails, use an email-to-webhook bridge, then call GitHub
`repository_dispatch` or commit raw email payloads through the GitHub API.

Recommended email ingress order:

1. Cloudflare Email Routing Worker. This is the default because Cloudflare
   documents Email Routing as available on Free and Paid plans, and Workers Free
   has enough request capacity for low-volume judgment notification capture.
2. Mailgun inbound parse. Use this only if its parsing/routing features are
   needed and a trial or paid plan is acceptable.
3. Scheduled mailbox polling through Gmail or IMAP. Use this only if webhook
   ingress is unavailable.

Historical and fallback-source captures must be archive-only. They must not
advance outbound syndication state or repost old material to X.

The GitHub-side receiver is the `Archive Email` workflow. It accepts
`repository_dispatch` events of type `courts_nz_email_received`, stores raw email
evidence under `historical_archive_raw/email/`, and writes normalized monthly
JSONL shards under `historical_archive_normalized/email/`. See
`docs/courts-nz-email-ingress.md` for the dispatch payload contract and
Cloudflare Worker handoff. The deployable Worker template lives at
`cloudflare/courts_nz_email_worker.mjs`, with a Wrangler configuration example
at `cloudflare/wrangler.courts-nz-email.toml.example`. The manual
`Deploy Email Worker` workflow deploys that Worker when these repository secrets
are configured:

- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`
- `EMAIL_WORKER_GITHUB_TOKEN`

The archive track publishes normalized corpus artifacts to Hugging Face Datasets
and citable release snapshots to Zenodo. Additional outbound syndication
accounts must be created as separate conductor tracks after the archive pipeline
is stable, with one platform/account per track, task-level commits, phase
reviews, and explicit posting contracts.

The `Publish Archives` workflow bundles the legacy archive, normalized
multi-source shards, raw evidence files, the Hugging Face dataset card, and the
corpus manifest into a downloadable Actions artifact. If `HF_TOKEN` and
`HF_DATASET_REPO_ID` are configured, the same workflow uploads the bundle to
Hugging Face Datasets. If `ZENODO_TOKEN` and `ZENODO_DEPOSIT_ENDPOINT` are
configured, it also uploads the same bundle to Zenodo.

The `Archive No-Op Monitor` workflow replays a known email archive payload and
fails if the duplicate capture changes `historical_archive_raw/email/` or
`historical_archive_normalized/email/`. This gives the archive pipeline a
scheduled duplicate-ingress guard without depending on live source feeds.

The `Archive Compaction Manifest` workflow runs monthly and writes only
`conductor/archive_compaction_manifest.json`. It records source/month counts,
byte sizes, full content checksums for normalized JSONL shards, and path/size
inventory digests for raw shards without deleting, rewriting, or repacking
archive records. The `Publish Archives` workflow also includes the same
manifest in the generated corpus artifact so Hugging Face and Zenodo
publication can verify the Git-held shards against the dataset bundle.

## 7. Source Discovery and Ingestion Tools

Runtime dependencies are in `requirements.txt`.

- RSS/Atom: `feedparser`
- Bluesky/AT Protocol posting: `atproto`
- Video metadata: `yt-dlp`
- Optional social profile probing: `social-analyzer`
- Deferred X outbound posting: Buffer CLI, with Tweepy/X API v2 as fallback
- Future archive adapters: AT Protocol/Bluesky, LinkedIn export/API, X archive
  capture, inbound email parsing, and Hugging Face dataset publishing

Candidate profile discoveries must be reviewed before editing
`registry/agencies.json`.

## 8. Validate Secrets

Run the validator locally:

```powershell
python scripts/validate_secrets.py --mode syndicate
python scripts/validate_secrets.py --mode archive
```

Local validation reads `.env.local` when present, then lets exported process
environment variables override those values. GitHub Actions uses repository
secrets directly.

The syndication workflow runs the validator before posting.

The `Syndicate` workflow runs on schedule. Manual dispatch still requires
`confirm_live_posting=true` when you intend to publish new mirrored posts.

## 9. Local Quality Gate

```powershell
ruff check --no-cache src tests scripts
pytest -q
python scripts/gap_analyzer.py --registry registry/agencies.json --output registry/gap_analysis.json
python scripts/build_archive_compaction_manifest.py --normalized-dir historical_archive_normalized --raw-dir historical_archive_raw --output conductor/archive_compaction_manifest.json
python scripts/publish_archives.py --archive-dir historical_archive --normalized-dir historical_archive_normalized --raw-dir historical_archive_raw --output-dir dist --manifest dist/archive_manifest.json
```

## 10. Upstream Fixes

If an external tool needs a fix, use `scripts/upstream_contribution.py` and the
upstream manifest in `config/upstream_tools.json`. Open an upstream issue, fork
into this GitHub account, implement the fix in the fork, and submit a PR.
