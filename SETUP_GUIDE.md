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

## 2. Preferred Outbound Posting: Buffer

The MVP can syndicate Courts of New Zealand Bluesky posts to X through Buffer's
official CLI. This avoids direct X API credits when Buffer's connected X channel
supports automatic publishing.

Required GitHub secrets:

- `BUFFER_API_KEY`
- `BUFFER_X_CHANNEL_ID`

Local setup:

```powershell
npm install -g @bufferapp/cli
buffer doctor --output json
buffer channels list --organization-id <organization-id> --output json
```

Generate a Buffer API key at `https://publish.buffer.com/settings/api`, connect
`@MirNZCourts` as an X channel in Buffer, then set `BUFFER_X_CHANNEL_ID` to that
channel ID.

After adding both secrets, run the `Validate Buffer Syndication` workflow. It
checks the Buffer account and dry-runs the exact X post command without
publishing.

## 3. Direct X API Fallback

Direct X API posting through Tweepy remains available as a fallback, but it
requires X developer API credits.

Required GitHub secrets:

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
- Threads: `THREADS_API_ENDPOINT`, `THREADS_ACCESS_TOKEN`
- LinkedIn: `LINKEDIN_API_ENDPOINT`, `LINKEDIN_ACCESS_TOKEN`

## 5. Archive Publishing

For external archive publishing, configure:

- Zenodo: `ZENODO_TOKEN`, `ZENODO_DEPOSIT_ENDPOINT`
- Hugging Face: `HF_TOKEN`, `HF_DATASET_REPO_ID`

The Pages workflow builds a local archive bundle. Publishing to external archive
services is controlled by the publishing script and environment credentials.

## 6. Courts of New Zealand Multi-Source Archive

The Courts of New Zealand archive expansion is tracked in
`conductor/tracks/courts_nz_multisource_archive_20260612/`.

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

The archive track publishes normalized corpus artifacts to Hugging Face Datasets
and citable release snapshots to Zenodo. Additional outbound syndication
accounts must be created as separate conductor tracks after the archive pipeline
is stable, with one platform/account per track, task-level commits, phase
reviews, and explicit posting contracts.

## 7. Source Discovery and Ingestion Tools

Runtime dependencies are in `requirements.txt`.

- RSS/Atom: `feedparser`
- Video metadata: `yt-dlp`
- Optional social profile probing: `social-analyzer`
- Outbound posting: Buffer CLI, with Tweepy/X API v2 as fallback
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
python scripts/publish_archives.py --archive-dir historical_archive --output-dir dist --manifest dist/archive_manifest.json
```

## 10. Upstream Fixes

If an external tool needs a fix, use `scripts/upstream_contribution.py` and the
upstream manifest in `config/upstream_tools.json`. Open an upstream issue, fork
into this GitHub account, implement the fix in the fork, and submit a PR.
