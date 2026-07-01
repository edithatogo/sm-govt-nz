# Repository Management

This repo is script and workflow heavy, so the management guardrails focus on
keeping automation deterministic and easy to inspect.

## Validation entrypoints

- Local quick validation: `.\scripts\validate_repo.ps1 quick`
- Local workflow validation: `.\scripts\validate_repo.ps1 workflows`
- Local full validation: `.\scripts\validate_repo.ps1 full`

The local wrappers run through `uv run --python 3.14` so validation does not
depend on the Windows Store `python` alias. CI enforces the same project Python
version.

## Workflow contracts

Workflow behavior that affects archive state should have a focused contract test
under `tests/`. Prefer these assertions for:

- committed report and summary paths;
- publication guard behavior;
- issue-opening policy;
- archive artifact names;
- required Python version;
- dry-run versus live-capture boundaries.

GitHub Actions YAML is linted with `actionlint` in CI. If `actionlint` is
installed locally, `.\scripts\validate_repo.ps1 workflows` runs it before the
workflow contract tests.

## State artifacts

Machine-readable report files under `conductor/` and `dist/` are the durable
source of truth for automation state. Compact Markdown summaries are for human
triage and should point back to the JSON report when detailed review is needed.

## Operating rules

- Keep scheduled workflows bounded with limits, offsets, and timeouts.
- Prefer sharded backlog runs for large historical captures.
- Commit reports separately from payload files unless a workflow explicitly opts
  into payload commits.
- Treat external publication state as canonical only when written to
  `conductor/archive_publication_status.json`.
- Reserve GitHub issues for actionable automation faults, not expected zero-input
  coverage gaps.
