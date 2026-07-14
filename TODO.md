# TODO — Future Work

Items identified as potential next steps but not yet started. Each can be tackled independently.

## MCP Server Improvements

- [ ] **Add manifest reload tool (KNOWN_ISSUES #15)** — The MCP server loads `semantic_manifest.json` at import time. Add a `reload_manifest()` MCP tool that re-reads the file on demand, or watch the file for changes. File: `src/mcp_server.py`
- [ ] **Install dbt-metricflow (KNOWN_ISSUES #16)** — Add `dbt-metricflow>=0.1.0` to `pyproject.toml` when MetricFlow's query resolution engine is needed for complex multi-model joins.
- [ ] **Automate Lightdash project setup (KNOWN_ISSUES #14)** — Add a bootstrap script that creates a Lightdash project, syncs dbt, and generates a Personal Access Token (PAT) via the API. Currently the Lightdash REST API tools require manual setup.

## Data Quality & Testing

- [ ] **Add dbt tests and data quality checks** — The Makefile has `dbt-test` but test coverage is thin. Add singular tests, schema tests (unique, not_null, relationships), and freshness checks to the mart models in `dbt_project/models/`.
- [ ] **Integrate Great Expectations or dbt expectations** — Add expectation checks as Dagster asset checks for pipeline-level data quality monitoring.

## CI/CD

- [ ] **Add GitHub Actions CI pipeline** — Set up workflows for: lint (ruff), typecheck, dbt parse/compile, and MCP integration tests (`src/test_mcp_server.py`). Run on push and PR.

## Observability & Alerting

- [ ] **Wire Dagster sensors for pipeline failure alerts** — Add sensors that notify on asset materialization failures or sensor errors.
- [ ] **Expose pipeline metrics to MCP server** — Add MCP tools that report pipeline run status, data freshness, and row counts from the latest runs.
- [ ] **Add data-quality monitoring hooks** — Surface data quality check results (from dbt tests or Great Expectations) through the MCP server or a dashboard.

## Performance & Scale

- [ ] **Benchmark full-scale data load** — Run the 50M+ row `make generate-full` path, benchmark DuckDB query performance over partitioned Parquet, and document throughput numbers in the README.
- [ ] **Optimize Parquet partitioning strategy** — Evaluate partition pruning performance with current `tenant_id/year/month` scheme and test alternative partition strategies.

## Remaining Known Issues (not blocking)

See [KNOWN_ISSUES.md](KNOWN_ISSUES.md) for issues that are documented but out of current scope:
- **#10** — Dagster daemon heartbeat conflicts on pod restart (non-fatal, auto-resolves in ~60s)
- **#13** — Lightdash built-in MCP server requires Enterprise license
- **#18** — Community `lightdash-mcp` package uses raw MCP SDK, not fastmcp
