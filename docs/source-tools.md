# Source Tool Integration

This repo uses source tools in narrow roles:

- `feedparser`: automated RSS/Atom ingestion for agency websites and media-release feeds.
- `yt-dlp`: metadata-only capture for public video and embedded media URLs.
- `social-analyzer`: optional operator-run discovery probe for candidate social profiles.
- `newsboat`: optional RSS/Atom feed health checks only; canonical parsing stays in Python.
- `feediverse`: out of scope for source archival because it republishes RSS/Atom to Mastodon.
- `RSSHub`: optional redundant X feed source using `/twitter/user/<handle>` routes.
- `Nitter-compatible feeds`: optional redundant X feed sources such as `xcancel.com/<handle>/rss`.
- `twscrape` and `Scweet`: disabled account-cookie scraper stubs unless explicitly enabled and configured by an operator.
- `gofeed`: reference if feed ingestion is later moved to Go.
- `build_archive_gap_map.py`: deterministic prioritisation of archive gaps into existing-resource fixes, manual-seed inputs, operator/API access, and larger browser/access projects.

Configuration lives in `config/source_tools.json`.

Production ingestion should normalize every source into the same post contract
used by the archive and syndication layers. Tools that discover candidate
profiles must not silently mutate `registry/agencies.json`; candidate findings
should be reviewed before being added.
