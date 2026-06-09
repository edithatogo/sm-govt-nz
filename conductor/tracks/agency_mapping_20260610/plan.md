# Plan - NZ Agency Social Registry & Self-Improving Agent Framework

## Phase 1: Registry Schema & Initial Data Seeding
- [ ] Task: Define the data schema for the agency registry (`registry/agencies.json`).
- [ ] Task: Seed the initial data for Courts of NZ, Ministry of Health, Health NZ, Parliament, and Beehive NZ.
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Registry Schema & Initial Data Seeding' (Protocol in workflow.md)

## Phase 2: Gap Analysis & Reporting Engine
- [ ] Task: Implement `scripts/gap_analyzer.py` to calculate social platform coverage metrics.
- [ ] Task: Add test suite using pytest to verify metric generation and JSON exporting.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Gap Analysis & Reporting Engine' (Protocol in workflow.md)

## Phase 3: Automated Episodic Registry Updater
- [ ] Task: Build a scheduled GitHub Action workflow that calls the verification script to check link health and update registry statistics.
- [ ] Task: Integrate registry statistics output directly into the public HTML Pages dashboard.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Automated Episodic Registry Updater' (Protocol in workflow.md)

## Phase 4: Self-Improving Agent Framework
- [ ] Task: Define SOTA agent conventions, prompt templates, and custom rules under `/agent_framework`.
- [ ] Task: Create a self-evaluation loop script (`scripts/self_eval.py`) that tests existing code quality, lints it, and automatically logs suggested skill/prompt upgrades.
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Self-Improving Agent Framework' (Protocol in workflow.md)
