# Project Workflow - NZ Government Bluesky Syndicator & Transparency Hub

## Development Cycle
We use **Trunk-Based Development** for rapid iteration and deployment:
1.  **Local Development:** Code is written and tested locally using `uv` for environment management.
2.  **Verification:** Run style checks, strict type checking (`ty`), and testing suites before pushing.
3.  **Direct Integration:** Commit changes directly to the `main` (or `master`) branch.
4.  **Automated CI/CD:** GitHub Actions triggers linting, testing, and deployment automatically upon pushing.

## Continuous Integration (CI) Quality Gate
A GitHub Actions workflow (`.github/workflows/ci.yml`) runs on every push and pull request to verify code quality:
*   **Prose Linting:** Check all markdown documents and product guides using the **Vale prose linter**.
*   **Code Linting & Formatting:** Enforce strict checks using **Ruff** (with security rules enabled via `S` prefix, replacing Bandit) and strict code formatting checks.
*   **Type Checking:** Run the **`ty` type checker in strict mode** (run via `uvx ty check`) to enforce complete type annotations.
*   **Testing Suites (>90% Test Coverage Target):**
    *   **Unit & Integration Tests:** Run mock-based testing using `pytest` and `vcrpy`.
    *   **End-to-End (E2E) & Smoke Tests:** Execute live API validation checks against test environments.
    *   **Property-Based Testing:** Enforce input boundaries and contract invariants using the `hypothesis` library.
    *   **Mutation Testing:** Run mutation checks using `mutmut` to verify test suite quality and coverage robustness.
    *   **Observability Loop:** Implement a mechanism to compare intended syndication state vs actual posted telemetry on target platforms to ensure execution accuracy.
*   **Dependency Management:** Automatically update and audit packages using **Renovate**.
*   **Profiling:** Use **Scalene** for performance and memory profiling to optimize loop execution times.

## Continuous Deployment & Execution (CD)
Two automated processes run on GitHub Actions:

### 1. The Syndicator Cron Job (`.github/workflows/syndicate.yml`)
*   **Schedule:** Runs every 15 minutes.
*   **Steps:**
    1.  Checkout repository code.
    2.  Set up Python environment and cache using `uv`.
    3.  Load the monitored account configuration and state file (`conductor/state.json`).
    4.  Fetch new posts and historical edits from Bluesky API.
    5.  Syndicate posts only to explicitly enabled mirror targets with completed platform contracts.
    6.  Archive posts and edits locally under `/historical_archive/`.
    7.  Update `conductor/state.json` with the new last-seen post IDs and telemetry logs.
    8.  Commit and push the updated state and archive files back to the repository.

### MVP Launch Gate - Courts of New Zealand to X
Before enabling the scheduled syndicator for the MVP:
1.  Merge the Courts of New Zealand mirror scope PR after CI passes.
2.  Confirm GitHub repository secrets for X posting validate with `scripts/validate_secrets.py --mode syndicate`.
3.  Keep `config.json` scoped to `courtsofnz.bsky.social` with `syndicate_to: ["x"]`.
4.  Confirm `conductor/state.json` is seeded to the latest known Bluesky post so historical posts are not reposted.
5.  Run one controlled `workflow_dispatch` or local dry/live test and verify the resulting X post links back to the source Bluesky post.
6.  Re-enable the GitHub `Syndicate` workflow only after the controlled test passes. The remote workflow is currently disabled manually as a safety gate.
7.  Monitor the first scheduled run and confirm `conductor/state.json` advances without duplicating posts.

### 2. GitHub Pages & External Archiving
*   **Trigger:** Runs on merges to `main` or scheduled weekly sweeps.
*   **Action:** Deploys the static root files to the public GitHub Pages site and packages/publishes historical datasets to external research repositories (Zenodo and Hugging Face).

### 3. Courts of New Zealand Multi-Source Archive Capture
*   **Trigger:** Runs alongside scheduled syndication, plus manual historical backfills.
*   **Action:** Captures archive-only records from current Bluesky, official LinkedIn, inactive historical X, Courts of NZ website/RSS feeds, and the judgments of public interest email subscription.
*   **Safety:** Archive-only records maintain separate state from outbound syndication so historical X, LinkedIn, RSS, and email backfills cannot be reposted. LinkedIn is source-only and must not be used for posting in the current roadmap.
*   **Dataset Publishing:** Normalized shards and raw-source bundles are prepared for Hugging Face Datasets, with Zenodo publication retained as a preservation lane.

### 4. New Mirror Platform Tracks
*   **Bluesky mirror:** Establish an unofficial mirror account under the systematic Courts of New Zealand mirror identity, separate from any personal Bluesky account.
*   **Threads mirror:** Establish an unofficial mirror account under the systematic Courts of New Zealand mirror identity, separate from any personal Instagram/Threads identity.
*   **Credential ownership:** Use `edithatogo@gmail.com` for account administration where practical, but never post under Dylan Mordaunt, `edithatogo`, or any personal identity.
*   **LinkedIn boundary:** LinkedIn remains an archive/source-ingestion lane only until a later explicit track reopens posting with separate risk review.
