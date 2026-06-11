# Repository Agent Rules

1. Inspect `git status --short --branch` before changing files.
2. Treat `registry/agencies.json` as source data and `registry/gap_analysis.json` as generated output.
3. Run `python scripts/gap_analyzer.py` after registry edits.
4. Run `ruff check --no-cache src tests scripts` and `pytest -q` before marking implementation work complete.
5. Do not post to external networks unless credentials are explicitly configured in the execution environment.
6. Keep manual verification tasks open until generated outputs and local gates have been checked.