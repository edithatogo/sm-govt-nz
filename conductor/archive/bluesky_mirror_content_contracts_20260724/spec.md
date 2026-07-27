# Specification

Define which normalized records are mirrorable. Require `source_kind=post` or a platform-equivalent post type; retain public profile snapshots as archive metadata only. Add `public_name` for concise mirror-facing names such as `ACC`, while preserving canonical agency identity. Use `<organisation-abbreviation>-<country-or-jurisdiction>-arc.bsky.social` for primary handles, with stable numbered collision suffixes. Validate long-post rendering and provenance links.

Acceptance requires profile snapshots to be rejected, actual posts to render deterministically, `ACC` to appear in public-facing mirror metadata, and the ACC handle to resolve as `acc-nz-arc.bsky.social`.
