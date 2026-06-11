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

## 2. Outbound Posting: X API

The MVP syndicates Courts of New Zealand Bluesky posts to X through direct X
API v2 posting with Tweepy.

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

## 3. Additional Platform Targets

- Discord: `DISCORD_WEBHOOK_URL`
- Mastodon: `MASTODON_BASE_URL`, `MASTODON_ACCESS_TOKEN`
- Threads: `THREADS_API_ENDPOINT`, `THREADS_ACCESS_TOKEN`
- LinkedIn: `LINKEDIN_API_ENDPOINT`, `LINKEDIN_ACCESS_TOKEN`

## 4. Archive Publishing

For external archive publishing, configure:

- Zenodo: `ZENODO_TOKEN`, `ZENODO_DEPOSIT_ENDPOINT`
- Hugging Face: `HF_TOKEN`, `HF_DATASET_REPO_ID`

The Pages workflow builds a local archive bundle. Publishing to external archive
services is controlled by the publishing script and environment credentials.

## 5. Source Discovery and Ingestion Tools

Runtime dependencies are in `requirements.txt`.

- RSS/Atom: `feedparser`
- Video metadata: `yt-dlp`
- Optional social profile probing: `social-analyzer`
- Outbound posting: Tweepy/X API v2

Candidate profile discoveries must be reviewed before editing
`registry/agencies.json`.

## 6. Validate Secrets

Run the validator locally:

```powershell
python scripts/validate_secrets.py --mode syndicate
python scripts/validate_secrets.py --mode archive
```

The syndication workflow runs the validator before posting.

## 7. Local Quality Gate

```powershell
ruff check --no-cache src tests scripts
pytest -q
python scripts/gap_analyzer.py --registry registry/agencies.json --output registry/gap_analysis.json
python scripts/publish_archives.py --archive-dir historical_archive --output-dir dist --manifest dist/archive_manifest.json
```

## 8. Upstream Fixes

If an external tool needs a fix, use `scripts/upstream_contribution.py` and the
upstream manifest in `config/upstream_tools.json`. Open an upstream issue, fork
into this GitHub account, implement the fix in the fork, and submit a PR.
