# Specification

Add optional `mirror_id` inputs to preflight, ongoing, backfill, health, and recovery workflows. Manual runs must select only the requested mirror; scheduled runs retain the enabled matrix. Use account-specific concurrency groups and make the selected matrix visible in run summaries.
