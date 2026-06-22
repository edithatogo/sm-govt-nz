# sm-govt-nz — Maturity Dependency Checklist

| Category | Status | Rationale |
|---|---|---|
| Python environment manager (uv/pixi) | `required` | uv already adopted: `uv.lock` resolves pyproject deps, `uv pip install` in CI, `uv python install 3.11` in 4+ workflows. Pixi not used and not needed. |
| Python lint/format (ruff) | `required` | Already configured in `pyproject.toml`. Current selection (E4, E7, E9, F) is very minimal — should expand to broader rule sets for maturity. |
| Python type checking (ty/pyright) | `optional` | tech-stack.md claims `ty` in strict mode via `uvx ty check`, but no config exists and the codebase uses `TypedDict` + `cast` without enforcement. Would require significant refactoring to pass strict mode. Adopt when the codebase is ready. |
| Python logging (loguru) | `required` | Declared in `pyproject.toml` deps and in `[tool.legal_nz]` convention. Not yet imported in any source file — should be adopted across the codebase. |
| Python CLI UX (typer/rich) | `optional` | Currently uses plain `argparse` in `scripts/cli.py`. Typer would provide auto-help and composition; Rich would improve output. Low urgency for current CI-driven usage. |
| Config/env loading (pydantic-settings) | `optional` | Config uses manual `json.load` + `TypedDict` + `cast` in `src/config.py`. Pydantic would add validation and env-based overrides. Worth adopting as the project scales. |
| Boundary validation (pydantic v2) | `optional` | No pydantic at all. Validation is inline manual checks (key presence, path existence). Pydantic would formalize contract validation for config, state, and archive schema. |
| Hot record serialization (msgspec) | `deferred` | State files use plain `json.dump`/`json.load`. msgspec would improve perf and schema enforcement, but current record volumes don't justify it. Revisit when archive scale increases. |
| Dataframes (polars) | `not_applicable` | No analytical or tabular workloads in the codebase. No dataframe processing needed. |
| Query validation (duckdb) | `not_applicable` | No SQL query workloads. All state is flat-file JSON. |
| Columnar data (pyarrow/Parquet) | `deferred` | `pyarrow` is in `requirements.txt` and used in `scripts/publish_archives.py` for Parquet export. Planned for normalized archive shards per tech-stack.md. Currently only a build-time dependency for publication. |
| JSON schema (jsonschema) | `optional` | Config and state files are validated with inline checks. A formal JSON Schema would improve error messages and enable auto-generation of docs/templates. |
| HTTP clients (httpx/requests) | `required` | `requests` is in `requirements.txt` and used (lazy-imported) in `scripts/publish_archives.py`. No `httpx`. Migrating to `httpx` would give async support and HTTP/2, but not urgent for current use. |
| Retry/backoff (tenacity) | `optional` | No retry logic in the codebase. Would add resilience for API calls (Bluesky, X, Meta, Zenodo, Hugging Face). Worth adopting as platform count grows. |
| HTML parsing (beautifulsoup4/selectolax) | `optional` | Not currently needed (data comes from APIs, RSS, email). Would be needed for future HTML-scraping sources. |
| Terminal UI (rich) | `optional` | Scripts use `print()` statements and `json.dump` for output. Rich would improve developer experience for local runs and CI logs. |
| Checksums/manifests | `optional` | No content-hash dedup or integrity verification. Compaction manifest exists but lacks checksums. Worth adopting for archive integrity guarantees. |
| Local vector store (lancedb) | `not_applicable` | No semantic search or embedding use case. Not relevant to the archiving/syndication mission. |
| Service vector DB (qdrant) | `not_applicable` | No vector search workloads. Same rationale as lancedb. |
| RAG orchestration (haystack) | `not_applicable` | No RAG or LLM-augmented retrieval pipeline. Not relevant. |
| HF publication (huggingface_hub/datasets) | `required` | `huggingface_hub` in `requirements.txt`, used in `scripts/publish_archives.py` via `HfApi`. Active in CI (`publish_archives.yml`). |
| Archive/DOI (Zenodo/OSF) | `required` | Zenodo publication workflow exists (`publish_zenodo_deposition.yml`) and is actively used. Zenodo token/endpoint managed as GitHub secrets. OSF not used. |
