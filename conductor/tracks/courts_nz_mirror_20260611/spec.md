# Specification - Courts of New Zealand Mirror

## Overview
Prioritize a single public-service mirror for Courts of New Zealand posts from Bluesky to X before expanding to other agencies or platforms.

## Functional Requirements
1. Monitor only `courtsofnz.bsky.social` for the initial live synchronization scope.
2. Syndicate only to X until additional platform credentials and account policies are configured.
3. Seed `conductor/state.json` from the current Bluesky feed so the first scheduled run does not repost historical Bluesky content.
4. Use the systematic display-name pattern `Mirror: Courts of New Zealand` for the mirror identity.
5. Document the future action to archive historical `@courtsofnz` Twitter/X posts and connect them to the same agency timeline.

## Operational Notes
- Public Bluesky author feeds are fetched through the unauthenticated public AT Protocol endpoint, so a Bluesky account is not required for public feed reads.
- The X handle should be short and clear. `@CourtsNZMirror` is the preferred candidate because X handle length constraints make `NewZealand` difficult to spell out.
- Changing the live X display name or handle must be done through the X account settings UI after confirming the exact target name and handle.
