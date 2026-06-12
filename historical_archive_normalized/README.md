# Normalized Archive Store

Normalized corpus records are appended to source-specific monthly JSONL shards:

- `bluesky/<yyyy-mm>.jsonl`
- `linkedin/<yyyy-mm>.jsonl`
- `x/<yyyy-mm>.jsonl`
- `rss/<yyyy-mm>.jsonl`
- `email/<yyyy-mm>.jsonl`

Records must validate against `src.archive_schema.NormalizedArchiveRecord`
before they are written. Parquet and bundled dataset outputs are generated from
these JSONL shards for Hugging Face and Zenodo publication.
