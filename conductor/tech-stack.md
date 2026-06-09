# Technology Stack - NZ Government Bluesky Syndicator & Transparency Hub

## Execution Environment & Infrastructure
*   **Runtime Engine:** GitHub Actions Runner (`ubuntu-latest`)
*   **Workflow Schedule:** GitHub Actions Cron Scheduler (`on: schedule` running every 15 minutes)

## Backend / Scripting Stack (Python)
*   **Language Version:** Python 3.11+
*   **Key Dependencies:**
    *   `atproto`: Official Python SDK for the AT Protocol (Bluesky integration).
    *   `requests`: General HTTP client for interacting with standard REST webhooks and APIs (Threads, Discord).
    *   `requests-oauthlib`: Simplifies OAuth 1.0a authentication required by the X (Twitter) API.
    *   `Mastodon.py`: Client library for the Mastodon/ActivityPub API (optional, or standard HTTP requests).

## State Management
*   **Database:** Git-backed flat-file state storage.
*   **Format:** `conductor/state.json` containing mappings of Bluesky handles to their latest successfully syndicated post IDs.
*   **Mechanism:** Automatic commit and push using the GitHub Actions bot user (`github-actions[bot]`).

## Frontend / Public Web Stack
*   **Hosting Platform:** GitHub Pages
*   **Technologies:** Vanilla HTML5, Modern CSS3 (responsive grid, CSS custom properties for styling tokens), and ES6+ JavaScript.
*   **Assets:** Self-contained styling and scripts. No Node/NPM build step required.
