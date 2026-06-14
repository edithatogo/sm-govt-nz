# Courts of New Zealand Dataset Publication Contract

## Hugging Face Dataset

- Dataset repo: value of `HF_DATASET_REPO_ID`, recommended as
  `edithatogo/courts-nz-public-notices`.
- Dataset title: Courts of New Zealand public notices multi-source archive.
- License field: `other`.
- Dataset card: generated as `dist/README.md` by `scripts/publish_archives.py`.
- Primary artifact: `normalized_archive.jsonl.gz`.
- Supporting artifacts: `normalized/`, `raw/`, `historical_archive.jsonl.gz`,
  and `corpus_manifest.json`.

The dataset card must state that records are captured from public Courts of New
Zealand source surfaces and that source-specific terms should be checked before
redistribution. Raw payloads are included for provenance unless size or platform
terms require a manual or gated upload.

## Zenodo Deposition

- Deposition endpoint: value of `ZENODO_DEPOSIT_ENDPOINT`.
- Access token: value of `ZENODO_TOKEN`.
- Upload type: dataset.
- Title: Courts of New Zealand public notices multi-source archive.
- Version policy: create a new version for each reviewed public release, with
  monthly releases preferred once the archive pipeline is stable.
- Citation fields: use the generated `corpus_manifest.json` checksum and record
  counts in the release notes.
- Communities: none required for the MVP; add a community only after confirming
  it matches the corpus scope.

Zenodo snapshots must be generated from the same `scripts/publish_archives.py`
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
