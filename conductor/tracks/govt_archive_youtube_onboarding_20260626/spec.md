# Spec - NZ Government Archive - multi-agency YouTube channel archival

## Problem
175 NZ government YouTube channels have been discovered across all agencies but no automated metadata capture is configured. Video metadata (title, description, published date, duration) needs to be archived.

## Scope
- Compile full list of NZ government YouTube channel URLs/IDs from registry and readiness matrix (175 channels)
- Map each channel to its parent agency
- Create per-agency YouTube source configs with channel IDs and RSS feed URLs
- Run initial metadata capture for all channels
- Set up scheduled weekly YouTube metadata capture

## Technical Approach
- Prefer YouTube channel RSS feeds for routine metadata capture (no API key needed)
- Use Data API only for resolver gaps
- Do NOT download video files - archive only metadata
- Store normalized metadata in `historical_archive_normalized/youtube/`
- Handle rate limits via RSS feeds where possible

## Acceptance Criteria
- All 175 YouTube channels are configured and capturing metadata
- Video metadata archived per channel with consistent schema
- Per-channel capture manifests available for downstream publication
- Scheduled weekly YouTube capture workflow is active and verified
