# Source Tool Integration

This repo uses source tools in narrow roles:

- `feedparser`: automated RSS/Atom ingestion for agency websites and media-release feeds.
- `yt-dlp`: metadata-only capture for public video and embedded media URLs.
- `social-analyzer`: optional operator-run discovery probe for candidate social profiles.
- `newsboat`: manual feed review only.
- `feediverse`: reference for RSS-to-Mastodon templates and de-duplication.
- `gofeed`: reference if feed ingestion is later moved to Go.

Configuration lives in `config/source_tools.json`.

Production ingestion should normalize every source into the same post contract
used by the archive and syndication layers. Tools that discover candidate
profiles must not silently mutate `registry/agencies.json`; candidate findings
should be reviewed before being added.
