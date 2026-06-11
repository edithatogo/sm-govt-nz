# Plan - Post Archiver, Edit Tracker & Zenodo/Hugging Face Publisher

## Phase 1: Local Archiver & Edit History Tracker
- [x] Task: Create the local archive manager script that writes post JSONs under `/historical_archive/`.
- [x] Task: Implement edit detection logic to track content updates and append them to `edit_history`.
- [x] Task: Add test suite using pytest and hypothesis to verify edit log formatting.
- [x] Task: Conductor - User Manual Verification 'Phase 1: Local Archiver & Edit History Tracker' (Protocol in workflow.md)

## Phase 2: Zenodo & Hugging Face Publishers
- [x] Task: Write publisher scripts using `huggingface_hub` and requests to upload archives.
- [x] Task: Integrate publisher execution into the CD workflow (`pages.yml`).
- [x] Task: Conductor - User Manual Verification 'Phase 2: Zenodo & Hugging Face Publishers' (Protocol in workflow.md)

## Phase 3: Historical Backfill Importer
- [x] Task: Implement a historical import script that parses archive files and populates the database and web timeline.
- [x] Task: Integrate unlisted posting controls for Mastodon backfills.
- [x] Task: Conductor - User Manual Verification 'Phase 3: Historical Backfill Importer' (Protocol in workflow.md)
