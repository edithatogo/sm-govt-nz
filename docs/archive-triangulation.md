# Archive triangulation

The canonical archive remains the repository's own capture pipeline. External
archives provide independent corroboration only.

`triangulate_wayback.py` queries Internet Archive Wayback CDX for bounded,
metadata-only evidence. It records capture timestamps, canonical archived URLs,
HTTP status, MIME type, and digest. It does not download snapshots, submit URLs,
post to platforms, or replace canonical records.

The report distinguishes `capture_metadata_found`, `no_capture_found`,
`unsupported_url`, and `provider_error`. Absence from Wayback is not evidence
that a source never existed. Future triangulation providers should follow the
same compact-provenance and no-republication policy.

Anna's Archive is intentionally excluded as an ingestion or corroboration
provider because its provenance and rights status are not suitable for this
government archive. Lawful alternatives include Common Crawl, National Library
of New Zealand web collections, and official agency archives.

`triangulate_common_crawl.py` queries the current Common Crawl CDX index and
stores only index metadata. A Common Crawl hit is independent corroboration,
not proof that the canonical source capture is complete.
