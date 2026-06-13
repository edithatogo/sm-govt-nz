# Bluesky Mirror Runbook

## Pause or Resume Posting
Use GitHub Actions workflow controls for the `Syndicate` workflow when a pause
is needed. Do not edit state files to pause posting unless the workflow itself
cannot be disabled.

## Inspect Current State
Check these files before and after each controlled run:

- `conductor/state.json` for new source-feed posts.
- `conductor/bluesky_backlog_state.json` for Bluesky-source archive backlog.
- `conductor/archive_mirror_state.json` for recovered X archive replay.
- `conductor/archive_mirror_coverage.json` for total coverage.

## Verify Public Posts
Run:

```powershell
python scripts/bluesky_mirror_smoke.py --actor mirnzcourts.bsky.social --min-posts 1
python scripts/check_archive_mirror_coverage.py
```

The smoke check is non-posting. It reads the public Bluesky mirror feed and
requires `Original:` attribution in the latest checked posts.

## Rollback Boundaries
Git state can be corrected with a follow-up commit if a state file advances
incorrectly. Public Bluesky posts cannot be rolled back through git; they must be
deleted or corrected through the mirror account using an approved account-access
path.

## Known Profile Gap
The public profile archive captured on 2026-06-13 shows the mirror account
`mirnzcourts.bsky.social` currently has no public display name, description, or
banner in the Bluesky profile API response. Fix this manually in the account UI
before treating the profile identity track as fully closed.
