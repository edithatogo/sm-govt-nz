---
license: other
task_categories:
- text-classification
- text-generation
language:
- en
pretty_name: New Zealand Government Social Media Corpus/Archive
tags:
- corpus
- social-media
- government
- new-zealand
- region:nz
- public-records
- rss
- bluesky
- threads
- youtube
---

# New Zealand Government Social Media Corpus/Archive

Canonical name: `corpus-social-media-government-nz`.

This dataset package contains normalized New Zealand government social media records, with RSS and adjacent public web source captures retained for discovery, provenance, and source-context evidence.

## Contents

- `normalized_archive.jsonl.gz`: combined normalized records from source/month shards.
- `normalized_archive.parquet`: combined normalized records in Parquet format.
- `normalized/`: source/month normalized JSONL shards.
- `raw/`: raw source payloads captured before normalization.
- `corpus_manifest.json`: checksums, coverage counts, date ranges, and known gaps.

## Source Coverage

- api: 13 records
- bluesky: 1612 records
- courtsofnz.govt.nz: 11 records
- email: 14 records
- json_feed: 16 records
- linkedin: 2 records
- rss: 3930 records
- website_page: 226 records
- x: 755 records
- youtube: 1833 records

## Provenance

Records are derived from New Zealand government social media and adjacent public source surfaces and preserve source platform, source account, source URL, capture timestamp, original timestamp, content hash, media references, raw path, and extraction method where available.

## Known Gaps

- Platform capture beyond website, RSS, and Bluesky requires approved APIs, exports, or manual import workflows before automated archiving.
- Newsletter and email subscription ingress is pending source-specific mailbox/routing setup.
- Raw-source bundles are included in the Actions artifact and full archive tarball; separate gated raw publication can be added if source terms require it.
