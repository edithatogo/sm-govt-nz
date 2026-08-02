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

- api: 14 records
- bluesky: 2617 records
- courtsofnz.govt.nz: 11 records
- email: 25 records
- facebook: 323 records
- json_feed: 17 records
- linkedin: 61 records
- rss: 3960 records
- website_page: 1827 records
- x: 769 records
- youtube: 2741 records

## Provenance

Records are derived from New Zealand government social media and adjacent public source surfaces and preserve source platform, source account, source URL, capture timestamp, original timestamp, content hash, media references, raw path, and extraction method where available.

## Rights and Licensing

The repository owner has approved this corpus for publication. The `license: other` metadata is intentional: repository code licensing does not replace source-specific rights, notices, or platform terms attached to individual records. Provenance fields identify the source and capture method so downstream users can assess reuse conditions.

## Intended Use

This corpus supports research, public-record preservation, reproducibility, and auditing of New Zealand government communications. It is not an authoritative government record, an endorsement of archived content, or a basis for automated decisions about individuals.

## Limitations

Coverage varies by agency, platform, source availability, and capture method. Deleted, edited, access-controlled, or platform-restricted material may be absent. Users should validate records against authoritative sources when accuracy or currency is material.

## Update Cadence and Persistence

Hugging Face is the rolling dataset surface updated through reviewed publication workflows. Zenodo provides immutable versioned snapshots with DOIs; the current release evidence is recorded in the owning repository.

## Known Gaps

- Platform capture beyond website, RSS, and Bluesky requires approved APIs, exports, or manual import workflows before automated archiving.
- Newsletter and email subscription ingress is pending source-specific mailbox/routing setup.
- Raw-source bundles are included in the Actions artifact and full archive tarball; separate gated raw publication can be added if source terms require it.
