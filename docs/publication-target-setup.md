# Publication Target Setup

Canonical dataset slug:

`corpus-social-media-government-nz`

Display title:

`New Zealand Government Social Media Corpus/Archive`

## Hugging Face

Target dataset repository:

`edithatogo/corpus-social-media-government-nz`

The generated dataset card includes:

- `pretty_name: New Zealand Government Social Media Corpus/Archive`
- `license: other`
- `task_categories: text-classification, text-generation`
- `language: en`
- tags: `corpus`, `social-media`, `government`, `new-zealand`,
  `public-records`, `rss`, `bluesky`

The publication workflow uploads:

- `README.md`
- `metadata/corpus_manifest.json`
- `data/normalized_archive.jsonl.gz`
- `data/normalized_archive.parquet`
- `bundles/historical_archive.tar.gz`

Hugging Face Collections are not configured in repository metadata. If a remote
HF Collection is created later, the dataset should be added to that collection
out-of-band while keeping this dataset slug unchanged.

## Zenodo

Title:

`New Zealand Government Social Media Corpus/Archive`

Keywords:

- `corpus`
- `social media`
- `government`
- `New Zealand`
- `public records`
- `RSS`
- `Bluesky`

Versioning:

Each monthly scheduled publication uses `archive_release_version` from GitHub Actions,
defaulting to a UTC timestamp ending in `-archive`.

Zenodo communities are not configured until a specific matching community is
chosen. This avoids assigning the corpus to an unrelated community. The DOI
release can be added to a community later without changing the canonical dataset
slug.

## Internal Collections

Agency/source labels such as `courts-nz` are internal source collections within
the corpus. They remain useful for filtering and provenance, but they are not
the dataset-level publication name.
