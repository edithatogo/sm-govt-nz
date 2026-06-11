# Plan - Courts of New Zealand Mirror

## Phase 1: Narrow Production Scope
- [x] Task: Restrict `config.json` to Courts of New Zealand as the only monitored account.
- [x] Task: Disable non-X syndication targets until those platform credentials and policies are ready.
- [x] Task: Seed `conductor/state.json` for `courtsofnz.bsky.social` to prevent a backlog repost.

## Phase 2: Mirror Identity
- [x] Task: Adopt `Mirror: Courts of New Zealand` as the systematic display-name pattern.
- [x] Task: Confirm and apply the live X display name and handle change.
- [x] Task: Archive the current source Bluesky profile and mirror X profile in the GitHub repository.
- [x] Task: Apply minimally modified mirror profile text that identifies the account as unofficial and links back to the Bluesky source.

## Phase 3: Controlled Launch
- [x] Task: Wait for CI to pass on the Courts mirror PR after profile archive and roadmap updates.
- [x] Task: Merge the Courts mirror PR into `master`.
- [x] Task: Confirm required GitHub X secret names exist for `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, and `X_ACCESS_TOKEN_SECRET`.
- [x] Task: Run an Actions-level X-only secret validation before any live syndication run.
- [ ] Task: Run a controlled single-account, X-only live synchronization test.
- [ ] Task: Verify the resulting X post on `@MirNZCourts` preserves source attribution and does not duplicate historical content.
- [ ] Task: Re-enable the scheduled `Syndicate` workflow after the controlled test passes.
- [ ] Task: Monitor the first scheduled run and confirm `conductor/state.json` advances without duplicate posts.

## Phase 4: Later Historical Archive
- [ ] Task: Archive historical `@courtsofnz` Twitter/X posts into the GitHub repository without triggering syndication.
- [ ] Task: Archive historical and ongoing `courtsofnz.bsky.social` Bluesky posts into the GitHub repository.
- [ ] Task: Connect historical X records and current Bluesky records into one Courts of New Zealand timeline.
- [ ] Task: Package the GitHub archive as a Courts of New Zealand corpus/dataset for later Zenodo deposition and Hugging Face Dataset publication.
