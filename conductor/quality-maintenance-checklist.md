# Quality & Maintenance Tooling Baseline — sm-govt-nz

| Tool            | Classification | Status       |
|-----------------|----------------|--------------|
| Vale            | Required       | Present      |
| Markdown style  | Required       | Missing      |
| Renovate        | Required       | Present      |
| Codecov         | Conditional    | Missing      |
| Scalene         | Optional       | Missing      |

## Notes

- **Vale**: `.vale.ini` present but minimal (only `Vale` base, no prose/write-good extension).
- **Markdown style**: `.markdownlint.json` missing — created from root template.
- **Renovate**: `renovate.json` already present with pip_requirements and github-actions package rules.
- **Codecov** (conditional): `pyproject.toml` has `[tool.coverage]` config, but CI runs tests without `--cov` and no Codecov upload step exists. Not currently applicable.
- **Scalene** (optional): No `[tool.scalene]` in `pyproject.toml`. Not currently used.
