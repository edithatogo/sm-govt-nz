# Dataset Naming Conventions

## Canonical Pattern

Dataset slugs use ordered, lowercase components separated by hyphens:

`<dataset-type>-<corpus-type>-<subject-or-scope>-<jurisdiction>`

For this repository:

- dataset type: `corpus`
- corpus type: `social-media`
- subject/scope: `government`
- jurisdiction: `nz`

Canonical dataset slug:

`corpus-social-media-government-nz`

Display title:

`New Zealand Government Social Media Corpus/Archive`

## Scope Decision

The repository name `sm-govt-nz` reflects the originating purpose: archiving New
Zealand government social media. RSS feeds and adjacent public web captures are
included as discovery, provenance, and source-context surfaces, but they do not
replace the dataset identity as a social media corpus/archive.

Agency or source-specific labels, such as `courts-nz`, identify collections
inside the corpus. They should not be used as the dataset-level publication name
unless a separate agency-specific release is intentionally created.

## Publication Targets

Hugging Face dataset repository:

`edithatogo/corpus-social-media-government-nz`

Zenodo title:

`New Zealand Government Social Media Corpus/Archive`

Common metadata tags and keywords:

- `corpus`
- `social-media` / `social media`
- `government`
- `new-zealand` / `New Zealand`
- `public-records` / `public records`
- `rss` / `RSS`
- `bluesky` / `Bluesky`
