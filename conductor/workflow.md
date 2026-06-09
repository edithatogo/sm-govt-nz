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
    5.  Syndicate posts to X, Threads, Mastodon, Discord, and LinkedIn.
    6.  Archive posts and edits locally under `/historical_archive/`.
    7.  Update `conductor/state.json` with the new last-seen post IDs and telemetry logs.
    8.  Commit and push the updated state and archive files back to the repository.

### 2. GitHub Pages & External Archiving
*   **Trigger:** Runs on merges to `main` or scheduled weekly sweeps.
*   **Action:** Deploys the static root files to the public GitHub Pages site and packages/publishes historical datasets to external research repositories (Zenodo and Hugging Face).
