# Threads API access blocked

Date observed: 2026-06-24

Latest archival observation: 2026-06-29

The Courts of New Zealand Threads mirror is blocked by Meta before content is
accepted for posting. A Threads-only backfill for the five missed court posts
failed for every pending post with:

```text
HTTP 400: {"error":{"message":"API access blocked.","type":"OAuthException","code":200}}
```

The same error is returned by the Threads profile probe, so this is an account,
app, permission, or token access problem rather than a post formatting problem.

The broader `corpus-social-media-government-nz` archive now also uses the
official Threads profile-post lookup path for registered public handles. On
2026-06-29, `Archive Threads Scheduled` selected all three registered Threads
archive sources and each returned:

```text
HTTP 400 OAuthException 200 API access blocked.
```

Current registered Threads archive sources:

- `nz-police-threads-newzealandpolice`: `https://www.threads.net/@newzealandpolice`
- `nzte-threads-nzte`: `https://www.threads.net/@nzte`
- `wellington-city-libraries-threads-wcl-library`: `https://www.threads.net/@wcl_library`

Numeric Threads user IDs are no longer the first blocker for public-profile
archive capture because the archive runner tries `/profile_posts?username=...`
before falling back to numeric user-ID capture. The active blocker is Meta API
access for the configured app/token.

While Meta API access is blocked, authorized exports can still be archived
through the manual seed fallback:

1. Copy `manual_archive_seeds/threads/README.template.json` to a source-specific
   filename under `manual_archive_seeds/threads/`.
2. Replace the example post list with posts from an operator-authorized Threads
   export or bounded capture.
3. Run `Validate Threads Manual Seeds`.
4. Run `Archive Threads Manual Seeds`.

## Pending post IDs

- `3mom5bzcekc2g`
- `3momf4jknxk2k`
- `3momhtdf62k2k`
- `3movx5nyv5s2e`
- `3movyzaflkc2e`

These IDs must remain in `conductor/target_delivery_state.json` under the
Threads `pending_post_ids` list until a successful Threads backfill posts them.

## Recovery steps

1. Restore Threads API access in the Meta developer dashboard for the app that
   issued the configured token.
2. Confirm the app has the Threads API product and the required permissions for
   the target account, including profile read and content publishing access.
3. Generate or refresh the long-lived access token for the configured
   `THREADS_USER_ID`.
4. Update the GitHub repository secrets:
   - `THREADS_ACCESS_TOKEN`
   - `THREADS_USER_ID`, if the target account changed
5. Run the `Validate Threads` workflow.
6. Run the `Archive Threads Scheduled` workflow and confirm the report no longer
   shows `threads_permission_error`.
7. After validation succeeds, run the `Courts Missing Mirror Backfill` workflow
   with:

```text
confirm_live_posting=true
targets=threads
post_ids=3mom5bzcekc2g,3momf4jknxk2k,3momhtdf62k2k,3movx5nyv5s2e,3movyzaflkc2e
```

## Verification evidence

- `Validate Threads` failing at the profile probe means the blocker is upstream
  of the posting payload.
- A Threads-only backfill failing with the same OAuth error for each pending
  ID means the five posts cannot be belatedly mirrored until Meta API access is
  restored.
- `Archive Threads Scheduled` selecting registered sources but reporting
  `threads_permission_error` means source registration and scheduling are
  working, but the configured Meta app/token cannot read Threads profile posts.
- `Archive Threads Manual Seeds` succeeding means the fallback path is working
  and the corpus can be published even before Meta restores API access.
- Bluesky and X delivery state should not be changed while resolving this
  blocker.
