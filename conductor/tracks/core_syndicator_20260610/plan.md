# Plan - Core Syndicator and Transparency Website (MVP)

## Phase 1: Project Setup & Ingestion Configuration
- [x] Task: Initialize configurations (`config.json` and `conductor/state.json`) and write loading logic.
- [x] Task: Write tests for configuration and state loader utilities.
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Project Setup & Ingestion Configuration' (Protocol in workflow.md)

## Phase 2: Bluesky Ingestion Engine
- [ ] Task: Implement Bluesky AT Protocol client fetcher to retrieve posts.
- [ ] Task: Write mock tests for the Bluesky fetching and filtering logic.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Bluesky Ingestion Engine' (Protocol in workflow.md)

## Phase 3: Syndication Adapters
- [ ] Task: Implement Discord webhook syndication adapter and test suites.
- [ ] Task: Implement Mastodon API syndication adapter and test suites.
- [ ] Task: Implement X (Twitter) OAuth 1.0a API syndication adapter and test suites.
- [ ] Task: Implement Threads Graph API syndication adapter and test suites.
- [ ] Task: Implement LinkedIn API syndication adapter and test suites.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Syndication Adapters' (Protocol in workflow.md)

## Phase 4: Runner & State Persistence
- [ ] Task: Implement main orchestration loop connecting ingestion to target adapters.
- [ ] Task: Implement automated state persistence logic that reads/writes to `conductor/state.json`.
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Runner & State Persistence' (Protocol in workflow.md)

## Phase 5: UI Dashboard & CI/CD Workflows
- [ ] Task: Build static HTML/CSS/JS dashboard page and open government context section.
- [ ] Task: Create GitHub Actions workflows for CI checks (`ci.yml`), cron schedule (`syndicate.yml`), and static site deployment (`pages.yml`).
- [ ] Task: Conductor - User Manual Verification 'Phase 5: UI Dashboard & CI/CD Workflows' (Protocol in workflow.md)
