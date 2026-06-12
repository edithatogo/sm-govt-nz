# Initial Concept

What I'm wanting to do is to identify NZ government social media posts which are restricted to bluesky, and syndicate them to twitter. I have a page of outputs from Google AI Mode that I can provide you when you're ready, which provides additional discussion and background.

---

# Product Guide - NZ Government Bluesky Syndicator & Transparency Hub

## Product Vision & Goal
This project automatically syndicates social media updates from NZ Government agencies that publish on Bluesky to clearly identified mirror accounts on other platforms (such as X/Twitter, Threads, Mastodon, and Discord) to ensure public information is freely and widely accessible. In addition, it hosts a public GitHub Pages site to provide transparency, background context, and advocacy for open government communication.

## Current MVP Launch Scope
The immediate MVP is intentionally narrower than the long-term product:
*   **Source:** `courtsofnz.bsky.social`.
*   **Mirror:** Bluesky account `mirnzcourts.bsky.social`, display name `Mirror: Courts of New Zealand`.
*   **Posting direction:** Source public records to approved mirror accounts only.
*   **Identity:** Mirror accounts must be presented as unofficial mirrors and link back to the source profile. Posts must never be made under Dylan Mordaunt, `edithatogo`, or any other personal identity.
*   **Safety:** The first live run must be manual or tightly controlled, with `max_posts_per_run: 1`, so the seeded `conductor/state.json` prevents historical backlog reposting.
*   **Archive:** Current source and mirror profile snapshots live under `profile_archive/courts-nz/2026-06-11/`. Historical and ongoing X, Bluesky, LinkedIn, RSS, website, and email-subscription capture is tracked in `courts_nz_multisource_archive_20260612` before Hugging Face and Zenodo dataset publication. LinkedIn is source-only and archive-only for now.

## Core Features

### 1. Multi-Platform Syndication Engine
*   **Source:** Monitor selected NZ government/public sector Bluesky accounts.
*   **Targets:** Automate cross-posting of approved posts to:
    *   **X (formerly Twitter)**
    *   **Threads**
    *   **Bluesky mirror accounts**
    *   **Mastodon**
    *   **Discord** (Webhooks / Bot channels)
    *   **LinkedIn source capture only** (posting deferred because it is a higher-risk environment)
*   **Format Integrity:** Handle character limits (X is 280 characters, Bluesky is 300) with thread-splitting or truncation. Keep rich formatting, embedded links, and image alt-text.
*   **MVP Constraint:** Platform posting remains disabled until the relevant mirror account, credential owner, posting contract, duplicate-prevention state, and review gates are complete for that platform.
*   **Account Ownership:** New mirror accounts should be created under `edithatogo@gmail.com` for administration where practical, but the public account identity and all posts must use the systematic mirror naming pattern, not a personal identity.

### 2. Monitoring & Account Discovery
*   Maintain a primary whitelist of target agency handles in a simple repository configuration file (e.g., `config.json`).
*   Support querying/fetching accounts dynamically from public Bluesky Starter Packs or Lists.

### 3. Serverless Execution (GitHub Actions)
*   Run the syndicator script on a scheduled cron job (e.g., every 15 minutes) inside GitHub Actions.
*   Maintain syndication state (last processed post IDs) securely in the repository history using automated git bot commits.
*   Protect credentials (API tokens) using GitHub Repository Secrets.

### 5. Transparency & Open Government Website (GitHub Pages)
*   Build and deploy a public-facing website explaining the project's background.
*   Clearly state the rationale: information published by government entities should not be restricted to walled gardens or single platform lock-ins, promoting the principles of Open Government.
*   List the currently monitored agencies and output channels.
