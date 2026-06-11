# Agent Framework

This folder defines repository-local conventions for agents that maintain the NZ Government Bluesky Syndicator and transparency dashboard.

## Structure

- `rules/`: operating rules for autonomous maintenance work.
- `skills/`: reusable repository tasks that can be executed by agents or humans.
- `prompts/`: prompt templates for recurring maintenance workflows.
- `evaluations/`: generated quality and self-evaluation reports.

## Operating Model

Agents must inspect repository state before editing, keep generated artifacts deterministic, run the local quality gate, and record any proposed workflow upgrades as reviewable files rather than silently changing process.