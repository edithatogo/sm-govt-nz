# New Zealand Government Social Media Corpus Publication Contract

Canonical dataset name: `corpus-social-media-government-nz`.

Display title: `New Zealand Government Social Media Corpus/Archive`.

The dataset naming convention is:

- dataset type: `corpus`
- corpus type: `social-media`
- subject/scope: `government`
- jurisdiction: `nz`

The Courts of New Zealand material remains a source/agency collection inside
the corpus under `courts-nz`; it is no longer the dataset-level publication
name.

See also:

- `docs/dataset-naming-conventions.md`
- `docs/publication-target-setup.md`

## Hugging Face Dataset

- Dataset repo: `edithatogo/corpus-social-media-government-nz`, or the value of
  `HF_DATASET_REPO_ID` when overridden.
- Dataset title: New Zealand Government Social Media Corpus/Archive.
- License field: `other`.
- Dataset card: generated as `dist/README.md` by `scripts/publish_archives.py`.
- Tags: `corpus`, `social-media`, `government`, `new-zealand`,
  `public-records`, `rss`, `bluesky`.
- Primary artifact: `normalized_archive.jsonl.gz`.
- Supporting artifacts: `normalized/`, `raw/`, `historical_archive.jsonl.gz`,
  and `corpus_manifest.json`.

The dataset card must state that records are captured from New Zealand
government social media and adjacent public source surfaces, including RSS and
web captures used for discovery, provenance, and source context. Source-specific
terms should be checked before redistribution. Raw payloads are included for
provenance unless size or platform terms require a manual or gated upload.

## Publication Cadence

The machine-readable cadence contract is
`config/corpus_social_media_government_nz_publication_cadence.json`.

- Archive capture: `Archive Sources` runs every 6 hours and is independent of
  outbound syndication.
- Hugging Face: the monthly scheduled `Publish Archives` run is the rolling
  dataset update lane and publishes only to Hugging Face when `HF_TOKEN` is
  configured.
- Manual `Publish Archives`: defaults to artifact-only. External publication
  requires `publish=true` and an explicit target: `huggingface`, `zenodo`, or
  `all`.
- Zenodo: remains a release-snapshot lane. DOI publication must use the
  dedicated `Publish Zenodo Deposition` confirmation phrase
  `publish-zenodo-doi`, or another reviewed release workflow.

Each `Publish Archives` run writes
`conductor/archive_publication_status.json`, recording whether the run was
artifact-only, Hugging Face-published, Zenodo-published, or a combined
manual publication.

## Zenodo Deposition

- Deposition endpoint: value of `ZENODO_DEPOSIT_ENDPOINT`.
- Access token: value of `ZENODO_TOKEN`.
- Upload type: dataset.
- Title: New Zealand Government Social Media Corpus/Archive.
- Keywords: `corpus`, `social media`, `government`, `New Zealand`,
  `public records`, `RSS`, `Bluesky`.
- Version policy: create a new archive version for each scheduled monthly
  release. Manual reviewed releases can override `archive_release_version`; when
  omitted, the workflow uses a UTC timestamp ending in `-archive`.
- Citation fields: use the generated `corpus_manifest.json` checksum and record
  counts in the release notes.
- Communities: none required for the MVP; add a community only after confirming
  it matches the corpus scope.

Zenodo DOI versions must be generated from the same `scripts/publish_archives.py`
bundle used for Hugging Face so the DOI release and live dataset share checksums
and provenance.

## Required Provenance

Every normalized record should preserve:

- source platform
- source account
- source kind
- source URL
- canonical URL
- original created timestamp
- captured timestamp
- content hash
- raw path
- media references
- extraction method

The generated `corpus_manifest.json` must include checksums, source counts, date
ranges, raw file counts, normalized shard counts, and known gaps.
