# Product Guidelines - NZ Government Bluesky Syndicator & Transparency Hub

## Editorial Tone & Communication Strategy
The tone of this project (both in syndicated posts and on the GitHub Pages website) should strike a balance between **professional civic service** and **advocacy for the open web**:
*   **Neutral & Fact-Driven:** When presenting syndicated content, the system must not add personal commentary. The focus is strictly on data portability and public service.
*   **Open Government Advocacy:** The transparency site should clearly explain *why* open access to government communications is essential. It should advocate for public information being hosted on open, standard networks rather than proprietary, closed-source ecosystems.

## Content & Syndication Guidelines

### MVP Identity Design
*   **Display name:** `Mirror: Courts of New Zealand`.
*   **Handle:** `@MirNZCourts`.
*   **Bio posture:** Use the source account's public-information scope, but replace any official-account claim with an explicit unofficial-mirror statement.
*   **Source link:** The profile text must include `courtsofnz.bsky.social` or an equivalent Bluesky source link.
*   **Images:** Use the Courts of New Zealand source profile image and banner as mirror identity assets, with repository snapshots archived under `profile_archive/courts-nz/2026-06-11/`.

### 1. Transparency & Attribution
*   **Original Source Links:** All syndicated posts on target platforms (X, Threads, Mastodon) should include a consistent link or attribution back to the original Bluesky post (e.g., `[Original: bsky.app/...]`).
*   **Syndication Notice:** A subtle marker or standard prefix/suffix should clearly identify that the post is automated and syndicated for accessibility (e.g., `🤖 Mirror:` or similar identifier if space allows).
*   **MVP Attribution:** Courts of New Zealand mirror posts must preserve the public record content without commentary and include enough source attribution to identify the originating Bluesky post.

### 2. Character Limit & Thread Management
*   **Thread Mapping:** If a Bluesky post exceeds the character limit of the target platform (specifically X at 280 characters), the engine should split the post into a structured thread.
*   **Media Handling:** All image attachments must be transferred alongside their corresponding Alt Text to maintain accessibility compliance.

### 3. Website Design & Rationale
*   **Accessibility First:** The public website must adhere to high accessibility standards (WCAG compliant contrast, screen-reader friendly).
*   **Content Sections:**
    *   **Dashboard:** Real-time list of monitored government accounts.
    *   **Open Government Rationale:** A detailed essay explaining the value of decentralized protocols (AT Protocol, ActivityPub) for public sector records.
    *   **Disclaimer:** Clear documentation stating that this is an automated public-service mirror and not an official government-operated service.
