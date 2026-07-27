# Archive Registry Readiness

Status: `complete_external_evidence_verified`

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
- DataCite:
  `https://api.datacite.org/dois/10.5281/zenodo.21383327` reports the DOI as
  findable and identifies the resource as a dataset.

## External synchronization evidence

The generated Hugging Face card now includes rights, intended-use, limitations,
and cadence disclosures. Hugging Face dataset pull request #2 was merged on
2026-07-27. Public read-back confirmed all four sections on `main`, and the
Croissant endpoint continued to return successfully. No dataset files or Zenodo
record content were changed by the metadata synchronization.
