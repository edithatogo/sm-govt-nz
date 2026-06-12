# Raw Archive Store

Raw source payloads are stored under source-specific monthly directories:

- `bluesky/<yyyy-mm>/`
- `linkedin/<yyyy-mm>/`
- `x/<yyyy-mm>/`
- `rss/<yyyy-mm>/`
- `email/<yyyy-mm>/`

Each adapter must write raw evidence before appending normalized JSONL records.
Historical and fallback-source captures are archive-only and must not alter
outbound syndication state.
