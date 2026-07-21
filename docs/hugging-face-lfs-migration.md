# Git LFS to Hugging Face migration

Large normalized archive baselines belong in the canonical Hugging Face dataset,
not GitHub LFS. GitHub retains orchestration, source registries, reports, and new
small archive deltas.

The one-time `Migrate Git LFS Archive to Hugging Face` workflow:

1. Checks out Git pointer files without consuming LFS bandwidth.
2. Downloads the already-published archive bundle from
   `edithatogo/corpus-social-media-government-nz` on its GitHub-hosted runner.
3. Extracts each LFS-tracked normalized file and verifies its SHA-256 and size
   against the Git LFS pointer.
4. Uploads the verified files under
   `archive/historical_archive_normalized/` in the Hugging Face dataset.
5. Publishes `metadata/git_lfs_migration_manifest.json` to Hugging Face.
6. Removes the corresponding pointers and LFS tracking rule from the GitHub
   repository only after every upload succeeds.

Publication and Pages workflows hydrate a temporary normalized tree from the
migration manifest. New Git-resident records are merged with the Hugging Face
baseline by record identifier, without modifying or recommitting the baseline.

The daily `Rollover Large Archive Deltas to Hugging Face` workflow prevents new
Git-resident normalized JSONL deltas from approaching GitHub's blob limit. At
50 MiB it verifies and downloads any existing Hugging Face baseline, merges the
delta by record identifier, uploads the replacement baseline, updates the
migration manifest, and only then removes the Git copy. Runs with no qualifying
files are successful no-ops. The threshold is deliberately below GitHub's hard
limit so ordinary daily capture commits retain operational headroom.

The migration never posts or mirrors social-media content. It only changes
archive storage and publication transport.

## GitHub quota after migration

The current branch no longer references Git LFS and no workflow requests an LFS
checkout. GitHub nevertheless retains historical LFS objects and continues to
count them toward storage quota. GitHub documents repository recreation or a
GitHub Support purge as the mechanisms for removing those remote objects. This
project does not rewrite history, delete, or recreate the repository
automatically because those operations would disrupt commit, issue, fork, and
release continuity.
