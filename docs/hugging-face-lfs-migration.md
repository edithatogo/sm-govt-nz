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

The migration never posts or mirrors social-media content. It only changes
archive storage and publication transport.
