# Threads API access blocked

Date observed: 2026-06-24

The Courts of New Zealand Threads mirror is blocked by Meta before content is
accepted for posting. A Threads-only backfill for the five missed court posts
failed for every pending post with:

```text
HTTP 400: {"error":{"message":"API access blocked.","type":"OAuthException","code":200}}
```

The same error is returned by the Threads profile probe, so this is an account,
app, permission, or token access problem rather than a post formatting problem.

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
6. After validation succeeds, run the `Courts Missing Mirror Backfill` workflow
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
- Bluesky and X delivery state should not be changed while resolving this
  blocker.
