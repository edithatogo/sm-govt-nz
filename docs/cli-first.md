# CLI-first entrypoints

Use `sm-govt-nz` before invoking repository scripts directly.

## Commands

- `sm-govt-nz --list` lists approved aliases.
- `sm-govt-nz <alias> -- <script-args>` dispatches to the existing script implementation.

## Approved aliases

- `archive-bluesky` -> `scripts/archive_bluesky_history.py`
- `archive-current` -> `scripts/archive_current_sources.py`
- `archive-email` -> `scripts/archive_email_payload.py`
- `archive-rss` -> `scripts/archive_rss_history.py`
- `check-blockers` -> `scripts/check_multisource_blockers.py`
- `check-disk` -> `scripts/check_local_disk_space.py`
- `compile-registry` -> `scripts/compile_registry.py`
- `profile-discovery` -> `scripts/profile_discovery.py`
- `publish-archives` -> `scripts/publish_archives.py`
- `self-eval` -> `scripts/self_eval.py`
- `validate-secrets` -> `scripts/validate_secrets.py`

## Policy

Existing `scripts/*.py` files remain implementation modules. New automation, conductor tracks, and swarm prompts should call the package CLI first, then add a new alias here when a repeated workflow is needed.
