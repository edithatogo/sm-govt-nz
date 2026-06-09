# Project Workflow - NZ Government Bluesky Syndicator & Transparency Hub

## Development Cycle
We use **Trunk-Based Development** for rapid iteration and deployment:
1.  **Local Development:** Code is written and tested locally.
2.  **Verification:** Run style checks and unit tests before pushing.
3.  **Direct Integration:** Commit changes directly to the `main` (or `master`) branch.
4.  **Automated CI/CD:** GitHub Actions triggers linting, testing, and deployment automatically upon pushing.

## Continuous Integration (CI)
A GitHub Actions workflow (`.github/workflows/ci.yml`) runs on every push and pull request to verify code quality:
*   **Linting & Formatting:** Checks Python code using `ruff check` and `ruff format --check`.
*   **Testing:** Runs unit and integration tests using `pytest`.
*   **HTML Validation:** (Optional) Basic checks for static site assets.

## Continuous Deployment & Execution (CD)
Two automated processes run on GitHub Actions:

### 1. The Syndicator Cron Job (`.github/workflows/syndicate.yml`)
*   **Schedule:** Runs every 15 minutes.
*   **Steps:**
    1.  Checkout repository code.
    2.  Set up Python and cache dependencies.
    3.  Load the monitored account configuration and state file (`conductor/state.json`).
    4.  Fetch new posts from Bluesky API and syndicate to X, Threads, Mastodon, and Discord.
    5.  Update `conductor/state.json` with the new last-seen post IDs.
    6.  Commit and push the updated `conductor/state.json` back to the repository using a git bot token.

### 2. GitHub Pages Deployment (`.github/workflows/pages.yml`)
*   **Trigger:** Runs on every push to `main` that modifies the static pages (HTML, CSS, JS).
*   **Action:** Deploys the static root files to the public GitHub Pages site.
