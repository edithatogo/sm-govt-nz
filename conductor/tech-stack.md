# Technology Stack - NZ Government Bluesky Syndicator & Transparency Hub

## Execution Environment & Infrastructure
*   **Runtime Engine:** GitHub Actions Runner (`ubuntu-latest`)
*   **Workflow Schedule:** GitHub Actions Cron Scheduler (`on: schedule` running every 15 minutes)
*   **Dependency Management:** **`uv`** (Rust-based Python package installer) and **Renovate** (automated package dependency manager).

## Backend / Scripting Stack (Python)
*   **Language Version:** Python 3.11+
*   **Type Checker:** **`ty` (in strict mode)** via `uvx ty check`
*   **Prose Linter:** **Vale** (for markdown validation)
*   **Profiler:** **Scalene** (high-precision CPU, GPU, and memory profiling)
*   **Key Dependencies:**
    *   `atproto`: Python SDK for the AT Protocol (Bluesky integration).
    *   `requests` / `requests-oauthlib`: HTTP client and OAuth authentication wrappers.
    *   `huggingface_hub`: SDK for committing structured datasets to Hugging Face.
*   **Testing Frameworks:**
    *   `pytest`: Core test runner.
    *   `vcrpy`: Mock recording and playback of HTTP requests.
    *   `hypothesis`: Property-based and contract testing.
    *   `mutmut`: Mutation testing engine.

## State & Registry Management
*   **State Store:** Git-backed local `conductor/state.json`.
*   **Local Archive Store:** Flat-file directory structure (`/historical_archive/<agency>/<post_id>.json`).
*   **Raw Multi-Source Archive Store:** Planned source/month sharded raw payloads under `/historical_archive_raw/<source>/<yyyy-mm>/`.
*   **Normalized Dataset Store:** Planned source/month JSONL or Parquet shards under `/historical_archive_normalized/<source>/`.
*   **Profile Archive Store:** Date-stamped profile evidence under `/profile_archive/<agency>/<yyyy-mm-dd>/`.
*   **External Archive Repositories:**
    *   **Zenodo:** Long-term preservation of JSON datasets with DOI citation.
    *   **Hugging Face Datasets:** Public research dataset publication from normalized archive shards.
    *   **Cloudflare Email Routing / Mailgun Inbound Parse:** Candidate inbound email bridges for Courts of NZ judgments subscription messages, because GitHub does not provide a native mailbox.
    *   **Hugging Face Datasets:** Live repository of syndicated public records.

## MVP Runtime Configuration
*   **Active source account:** `courtsofnz.bsky.social`.
*   **Active target:** Bluesky mirror only, via `BLUESKY_MIRROR_HANDLE` and `BLUESKY_MIRROR_APP_PASSWORD`.
*   **Remote workflow state:** `Syndicate` is available for controlled manual dispatch and scheduled bounded runs once credentials validate.
*   **Launch throttle:** `max_posts_per_run` is `1` for live posts and `backlog_max_posts_per_run` is `1` for historical Bluesky backlog batches.
*   **Backlog State Store:** Git-backed local `conductor/bluesky_backlog_state.json`, separate from live `conductor/state.json`.
*   **Archive Replay State Store:** Git-backed local `conductor/archive_mirror_state.json`, separate from live and Bluesky-source backlog state, for recovered historical X archive replay to Bluesky.
*   **Archive Coverage Report:** `conductor/archive_mirror_coverage.json` records source counts, target counts, remaining records, and backdating support.
*   **Non-MVP targets:** X, Threads, Mastodon, Discord, and LinkedIn remain disabled in `config.json`; Threads has a no-posting readiness gate only.

## Frontend / Public Web Stack
*   **Hosting Platform:** GitHub Pages
*   **Technologies:** Vanilla HTML5, Modern CSS3 (responsive grid, CSS custom properties), and ES6+ JavaScript.
