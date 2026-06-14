# Specification - Automated Bi-Directional Mirror Follow Sync

## Overview
This track implements automated bi-directional following across all active New Zealand government mirror accounts (Twitter/X, Bluesky, Threads, and Instagram) on a daily schedule. To align with project safety and complexity limits, we focus first on relationship mapping and state redundancy before executing follows on the core mirror group.

---

## Phased Roadmap

### Phase 1: Relationship Mapping (Current Scope)
*   **Target Mapping:** Parse the config files to build a bi-directional follow requirements matrix (who should follow whom).
*   **Follow Verification Probes:** Implement read-only probes to check current follow status across all target accounts without making modification requests.

### Phase 2: Archiving & Follow State Redundancy (Current Scope)
*   **State Cache:** Create `conductor/follow_sync_state.json` to persist the verified follow states and prevent redundant API/browser operations.
*   **Cookie/Credential Management:** Define secure management guidelines for Playwright session storage/cookies without committing private keys.

### Phase 3: Core Group Follow Sync Execution (Current Scope)
*   **API Write Execution:** Implement programmatic follows for Bluesky (AT Protocol) and Twitter/X (Tweepy).
*   **Stealth Browser Fallback:** Implement Playwright stealth follow scripts for Threads and Instagram.
*   **Syndicate Workflow Integration:** Add a daily check step to `.github/workflows/syndicate.yml`.

### Phase 4: Wider Group Scaling (Future Scope)
*   **Auto-Onboarding Sync:** Auto-sync follows for any newly registered agency mirror accounts when they are added to the directory.

---

## Functional Requirements
1.  **Registry Relationship Matrix:**
    *   Identify all active mirror accounts and map bi-directional follow status.
2.  **Follow Execution Adapter:**
    *   `scripts/sync_mirror_follows.py` executes follows using direct APIs where available (Bluesky, Twitter/X) and headless browser automation as a fallback (Threads, Instagram).
3.  **Scheduled Action:**
    *   Integrate follow-sync checks into the daily automated workflow cycle.

## Acceptance Criteria
- `scripts/sync_mirror_follows.py` compiles and correctly identifies missing follows.
- Read-only probes accurately check follow status on all four platforms.
- Programmatic and Playwright follow execution succeeds for core mirror accounts.
- Follow state cache is committed to `conductor/follow_sync_state.json`.
