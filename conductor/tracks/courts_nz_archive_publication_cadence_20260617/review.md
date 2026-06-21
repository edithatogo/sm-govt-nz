# Track Review - Courts of New Zealand Archive Publication Cadence

**Track ID:** `courts_nz_archive_publication_cadence_20260617`  
**Review Date:** 2026-06-21  
**Reviewer:** Conductor Review System  
**Track Status:** `completed` (12/12 tasks)

---

## 1. Spec Compliance

| # | Requirement | Status | Evidence |
|---|-------------|--------|----------|
| R1 | Archive capture independent of outbound syndication | ✅ **Pass** | `archive_sources.yml` runs every 6h (`7 */6 * * *`) and is completely separate from `syndicate.yml` (15-min cron) and `publish_archives.yml` (weekly). Guardrail `archive_capture_independent_of_outbound_syndication: true` in cadence config. |
| R2 | Regular Hugging Face dataset updates | ✅ **Pass** | `publish_archives.yml` scheduled weekly (`41 16 * * 0`). Scheduled runs use `ARCHIVE_PUBLICATION_TARGET=huggingface`. Requires `HF_TOKEN` secret. |
| R3 | Zenodo as deliberate citable snapshot lane | ✅ **Pass** | `publish_zenodo_deposition.yml` is manual-only (`workflow_dispatch`), requires explicit `confirm: publish-zenodo-doi` string. Cadence: `manual_release_snapshot`. Guardrail: `scheduled_runs_must_not_publish_zenodo: true`. |
| R4 | Manual publish defaults to artifact-only | ✅ **Pass** | `publish_archives.yml` default `publish: false`. `ARCHIVE_PUBLICATION_TARGET` resolves to `artifact` when not scheduled and publish is false. Script only calls `--publish` when target is not `artifact`. |
| R5 | Publication status visible from committed reports | ✅ **Pass** | `conductor/archive_publication_status.json` written by `publish_archives.py`, committed by `commit_state_updates.py`. Records `mode`, `requested_targets`, `artifact`, `hugging_face`, `zenodo`. |

---

## 2. Plan Completion

| Phase | Tasks | Status |
|-------|-------|--------|
| **Phase 1:** Current Behavior Audit | 3/3 | ✅ Complete |
| **Phase 2:** Hugging Face Cadence | 3/3 | ✅ Complete |
| **Phase 3:** Zenodo Cadence | 3/3 | ✅ Complete |
| **Phase 4:** Closeout | 3/3 | ✅ Complete |


All 12 plan tasks are marked `[x]`. `conductor/setup_state.json` confirms `done: 12 / total: 12`.

---

## 3. Deliverables Assessment

### Cadence Configuration
| Artifact | Path | Quality |
|----------|------|---------|
| Machine-readable contract | `config/courts_nz_archive_publication_cadence.json` | Well-structured; defines archive capture, Hugging Face, Zenodo, manual publish, status report, and guardrails with explicit field-level documentation. |
| Publication documentation | `docs/courts-nz-dataset-publication.md` | Covers dataset card, Hugging Face cadence, Zenodo deposition, manual publish behavior, and provenance requirements. |
| Status report (latest) | `conductor/archive_publication_status.json` | Shows artifact-only run: 4591 files, 4213 normalized records, SHA256 committed. |
| Publication report (historical) | `conductor/archive_publication_report_20260614.json` | Full audit trail of Hugging Face upload (5 paths, 200 OK) and Zenodo DOI publication (deposition 20690547, state: `done`, submitted: true). |

### Workflow implementations
| Workflow | Key feature | Assessment |
|----------|-------------|------------|
| `publish_archives.yml` | Scheduled vs manual target routing via `ARCHIVE_PUBLICATION_TARGET` env var | ✅ Clean expression: scheduled → `huggingface`, manual with `publish=true` → user choice, manual without publish → `artifact`. |
| `publish_zenodo_deposition.yml` | `publish-zenodo-doi` confirmation gate | ✅ Deliberate friction: requires exact string match, no accidental DOI publication. |
| `archive_sources.yml` | Independent 6-hourly capture | ✅ Completely decoupled from syndication and publication workflows. |

### Test coverage
| Test | Purpose | Status |
|------|---------|--------|
| `test_archive_publication_cadence_config.py` | Validates cadence config guardrails | ✅ 1 passed |

---

## 4. Findings & Observations

### ✅ Strengths
1. **Machine-readable contract** — `config/courts_nz_archive_publication_cadence.json` makes the cadence explicit and testable, rather than relying on documentation alone.
2. **Safety by design** — Scheduled runs explicitly prohibited from publishing Zenodo. Manual runs default to artifact-only. Zenodo requires a confirmation phrase. These are all encoded as guardrails in the config and enforced in workflow logic.
3. **Publication status tracking** — Every run (artifact-only or published) writes a committed report. Freshness is checked via `source_git.freshness_status` in the status report.
4. **Independent lanes** — Archive capture (6h), syndication (15min), and publication (weekly) are completely independent, preventing cascading failures.

### ⚠️ Minor Issue
1. **`archive_sources.yml` still uses `pip` instead of `uv`** — Line 23 uses `python -m pip install -r requirements.txt`. The `publish_archives.yml` (line 60) also still uses `pip`. These predate this track and are out of scope for the cadence change, but are inconsistent with the `workflow.md` recommendation and the migration done in `ci.yml` and `syndicate.yml`.

### ℹ️ Notes
- The existing Zenodo DOI (`10.5281/zenodo.20690547`) and Hugging Face dataset (`edithatogo/courts-nz-public-notices-archive`) are already published and verified.
- The multi-source archive track (`courts_nz_multisource_archive_20260612`) points to this track for publication operations. 5 open tasks remain in that track.

---

## 5. Verdict

| Criterion | Result |
|-----------|--------|
| All spec requirements implemented | ✅ **Pass** |
| All plan phases/tasks completed | ✅ **Pass** |
| Cadence contract machine-checkable | ✅ **Pass** |
| Guardrails documented and enforced | ✅ **Pass** |
| Workflows implement cadence correctly | ✅ **Pass** |
| Publication status committed and visible | ✅ **Pass** |

**Overall: ✅ Track Complete — Ready to close.** No blocking issues.
