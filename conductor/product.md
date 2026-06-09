# Initial Concept

What I'm wanting to do is to identify NZ government social media posts which are restricted to bluesky, and syndicate them to twitter. I have a page of outputs from Google AI Mode that I can provide you when you're ready, which provides additional discussion and background.

---

# Product Guide - NZ Government Bluesky Syndicator & Transparency Hub

## Product Vision & Goal
This project automatically syndicates social media updates from NZ Government agencies that publish on Bluesky to other platforms (such as X/Twitter, Threads, Mastodon, Discord, and potentially LinkedIn) to ensure public information is freely and widely accessible. In addition, it hosts a public GitHub Pages site to provide transparency, background context, and advocacy for open government communication.

## Core Features

### 1. Multi-Platform Syndication Engine
*   **Source:** Monitor selected NZ government/public sector Bluesky accounts.
*   **Targets:** Automate cross-posting of 100% of posts to:
    *   **X (formerly Twitter)**
    *   **Threads**
    *   **Mastodon**
    *   **Discord** (Webhooks / Bot channels)
    *   **LinkedIn** (optional/extension)
*   **Format Integrity:** Handle character limits (X is 280 characters, Bluesky is 300) with thread-splitting or truncation. Keep rich formatting, embedded links, and image alt-text.

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
