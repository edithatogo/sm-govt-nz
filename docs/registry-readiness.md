# Archive Registry Readiness

Status: `published_evidence_verified_metadata_sync_pending`

Roadmap: `archive_registry_readiness_20260721`

- Parent issue: [#31](https://github.com/edithatogo/sm-govt-nz/issues/31)
- Rights and licensing: [#32](https://github.com/edithatogo/sm-govt-nz/issues/32)
- Zenodo/DataCite: [#33](https://github.com/edithatogo/sm-govt-nz/issues/33)
- Hugging Face/Croissant: [#34](https://github.com/edithatogo/sm-govt-nz/issues/34)

## Current contract

The canonical dataset is the New Zealand Government Social Media Corpus/Archive. Hugging Face is the rolling dataset surface and Zenodo is the immutable release-snapshot surface. The current publication metadata uses `license: other` because source-specific rights and redistribution conditions are not reducible to the repository code licence.

The repository owner has approved the corpus publication and rights scope.
Rights evidence must remain attached to source and record provenance. Public availability is not treated as blanket redistribution permission. Artifact-only, Hugging Face-published, Zenodo-published, and combined states remain distinct.

## Verified external evidence

Verified on 2026-07-27:

- Hugging Face dataset:
  `https://huggingface.co/datasets/edithatogo/corpus-social-media-government-nz`
  is public and enabled.
- Hugging Face Croissant:
  `https://huggingface.co/api/datasets/edithatogo/corpus-social-media-government-nz/croissant`
  returns metadata successfully.
- Zenodo record:
  `https://zenodo.org/records/21383327` is published with DOI
  `10.5281/zenodo.21383327`, open access, and five files.

## Remaining external boundary

The generated Hugging Face card now includes rights, intended-use, limitations,
and cadence disclosures. Those changes are repository-ready but are not claimed
as externally synchronized until a reviewed publication workflow updates the
public dataset README and the resulting card is read back.
