# Known Issues

Issues identified during development that are out of scope of the current phase but should be addressed in future work.

## Infrastructure

### 1. ~~Hardcoded hostPath in Dagster manifest~~ (Resolved)
**File:** `k3s/dagster.yaml`  
**Resolution:** Added clarifying comment documenting that `scripts/create_cluster.sh` dynamically maps `${REPO_ROOT}` to `/workspace/de-for-fun` inside the k3d container, making the hostPath portable regardless of where the repo is cloned on the host. Added an initContainer for permission normalization.

### 2. ~~MinIO uses `:latest` tag~~ (Resolved)
**File:** `k3s/minio.yaml`  
**Resolution:** Pinned MinIO image to `minio/minio:RELEASE.2024-07-16T23-46-30Z` for reproducible deployments.

### 3. ~~No health checks in k3s manifests~~ (Resolved)
**Files:** `k3s/minio.yaml`, `k3s/redpanda.yaml`, `k3s/dagster.yaml`, `k3s/lightdash.yaml`, `k3s/postgres.yaml`  
**Resolution:** Added `livenessProbe` and `readinessProbe` to all deployment containers: MinIO (HTTP health endpoints), Redpanda (TCP socket), Redpanda Console (HTTP), Dagster (HTTP), Lightdash (HTTP health API), and Postgres (`pg_isready`).

## Orchestration

### 4. ~~Empty Dagster definitions~~ (Resolved in Phase 4)
**File:** `src/orchestration/definitions.py`  
**Resolution:** Phase 4 implemented full Dagster asset definitions with 20 assets (generator -> buffer_writer -> verify -> 12 dbt models + time spine + 4 sources) using `dagster-dbt` for dbt model discovery.

### 5. ~~No automated Redpanda topic creation in deploy script~~ (Resolved)
**File:** `scripts/deploy.sh`  
**Resolution:** Replaced `|| true` fallback with `create_topic_with_retry()` function (3 retries, 2s backoff) that checks if a topic already exists before failing. Added a verification loop that confirms all 4 topics exist after creation.

## Data & Schema

### 6. ~~dbt base models reference non-existent `tenant_id` column~~ (Resolved in Phase 4)
**File:** `dbt_project/models/base/base_fan_pings.sql` (and all 3 other base models)  
**Resolution:** Phase 4 added `tenant_id` to the data generation schemas, partition paths, and buffer writer partitioning. All base models now correctly reference `tenant_id` as a hive partition column.

### 7. ~~PRD partition path includes `tenant_id` but implementation omits it~~ (Resolved in Phase 4)
**File:** `src/config.py` (`build_partition_path`)  
**Resolution:** Phase 4 updated `build_partition_path()` to include `tenant_id={tenant_id}/` in the partition path, matching the PRD §3 specification. Generators now produce `tenant_id` and the buffer writer partitions by it.

## Semantic Layer

### 8. dbt-metricflow not installed
**File:** `pyproject.toml`  
**Issue:** The `dbt-metricflow` package is not in dependencies. Semantic model YAML definitions are created in Phase 4 (4 semantic models, 8 metrics), and `dbt parse` validates them, but the `dbt sl query` command for running metric queries requires this package. It is needed for Phase 5 (Lightdash MCP Server) to query metrics programmatically.  
**Suggested fix:** Add `dbt-metricflow>=0.1.0` to `pyproject.toml` in Phase 5.

### 9. ~~Existing MinIO data lacks `tenant_id` partition~~ (Resolved during Phase 4 testing)
**Files:** MinIO `data-lakehouse` bucket  
**Resolution:** Old data was cleared from the bucket and regenerated with `make generate ROWS=10000 && make buffer`. New data uses the `tenant_id={tenant_id}/year=YYYY/month=MM/` partition format. All 4 dbt base models, staging views, and mart tables build successfully against this data.

## Testing & Operations

### 10. Dagster daemon heartbeat conflicts on pod restart
**File:** `k3s/dagster.yaml`  
**Issue:** When the Dagster pod restarts (e.g., via `kubectl rollout restart`), the new pod's daemons log ERROR-level messages about "Another SENSOR/BACKFILL/ASSET/SCHEDULER daemon is still sending heartbeats." This is because the Dagster home directory (`/app/data/dagster_home`) is on a shared PVC (`duckdb-pvc`), so old daemon heartbeat state persists across pod restarts.  
**Impact:** Non-fatal — the webserver serves correctly and all 20 assets load. The conflicts resolve once old heartbeats expire (~60 seconds).  
**Suggested fix:** Add an init container that clears the `dagster_home/heartbeat` directory on pod startup, or configure a shorter heartbeat TTL in `dagster.yaml`.

### 11. ~~`data/` directory owned by root causes DuckDB persistence failure~~ (Resolved)
**Files:** `src/mount_duckdb.py`, `src/query_duckdb.py`, `src/verify_data.py`, `Makefile`  
**Resolution:** Changed default DuckDB path in all three scripts from `data/compute.duckdb` to read the `DUCKDB_PATH` env var with an absolute default of `dbt_project/target/dev.duckdb` (computed from `__file__`). Updated Makefile `mount`, `query`, and `verify` targets to set `DUCKDB_PATH=$(CURDIR)/dbt_project/target/dev.duckdb`, consistent with dbt targets. The `data/` directory is no longer used for DuckDB storage.

### 12. ~~dbt `DUCKDB_PATH` must be absolute when running from repo root~~ (Resolved)
**File:** `dbt_project/profiles.yml`  
**Resolution:** Changed the default path from `dbt_project/target/dev.duckdb` to `target/dev.duckdb` (relative to `--project-dir`, not CWD). When running `dbt run --project-dir dbt_project --profiles-dir dbt_project` from the repo root, the path now correctly resolves to `dbt_project/target/dev.duckdb`. The Makefile continues to set an absolute `DUCKDB_PATH` for all dbt targets.

## Semantic Layer & MCP Server

### 13. Lightdash built-in MCP server requires Enterprise license
**File:** `k3s/lightdash.yaml`  
**Issue:** Lightdash's native `/api/v1/mcp` endpoint (StreamableHTTP transport, ~20 tools including `run_metric_query`, `render_chart`, `run_sql`) requires `MCP_ENABLED=true` and `LIGHTDASH_LICENSE_KEY` for self-hosted deployments. Our k3s manifest has neither.  
**Workaround:** The custom MCP server (`src/mcp_server.py`) queries DuckDB directly via the dbt semantic manifest, bypassing the need for Lightdash's Enterprise MCP. Community alternatives also exist: `lightdash-mcp` (Python, PyPI) by poddubnyoleg and `lightdash-mcp-server` (TypeScript, npm) by syucream.  
**Suggested fix:** If Enterprise features are needed, add `MCP_ENABLED=true` and a valid `LIGHTDASH_LICENSE_KEY` to the Lightdash deployment env vars.

### 14. Lightdash project setup not automated
**Files:** `k3s/lightdash.yaml`, `src/mcp_server.py`  
**Issue:** The optional Lightdash REST API tools (`lightdash_status`, `lightdash_list_charts`, `lightdash_get_catalog`) require a running Lightdash instance with a configured project, dbt sync, and a Personal Access Token (PAT). No automation script exists for this setup.  
**Workaround:** The primary MCP path (DuckDB + semantic manifest) works without Lightdash. The Lightdash tools gracefully report "not configured" when `LIGHTDASH_URL` and `LIGHTDASH_TOKEN` env vars are not set.  
**Suggested fix:** Add a bootstrap script that creates a Lightdash project, syncs dbt, and generates a PAT via the API.

### 15. MCP server reads stale semantic manifest
**File:** `src/mcp_server.py`  
**Issue:** The MCP server loads `semantic_manifest.json` at module import time. If dbt models or metrics change (via `make dbt-run`), the server must be restarted to pick up the new definitions.  
**Suggested fix:** Add a `reload_manifest()` MCP tool that re-reads the manifest on demand, or watch the file for changes.

### 16. `dbt-metricflow` still not installed
**File:** `pyproject.toml`  
**Issue:** The `dbt-metricflow` package is not in dependencies (existing issue #8). The MCP server queries DuckDB directly instead of using `dbt sl query`, so this is not blocking for Phase 5. However, if future work wants to use MetricFlow's query resolution engine (e.g., for complex multi-model joins), the dependency is still needed.  
**Suggested fix:** Add `dbt-metricflow>=0.1.0` to `pyproject.toml` when MetricFlow integration is required.

### 17. ~~Chart output directory defaults to `dbt_project/target/charts/`~~ (Resolved)
**File:** `src/config.py`, `.gitignore`  
**Resolution:** Changed the default `CHART_OUTPUT_DIR` from `dbt_project/target/charts` to a top-level `charts/` directory at the project root. This is always writable and not cleared by `dbt run`. Added `charts/` to `.gitignore`.

### 18. Community `lightdash-mcp` package uses raw MCP SDK, not fastmcp
**Files:** `pyproject.toml`, `src/mcp_server.py`  
**Issue:** The community `lightdash-mcp` PyPI package by poddubnyoleg uses `mcp.server.Server` (raw MCP SDK) while our project uses `fastmcp` (which wraps `mcp` internally). The two frameworks do not compose natively in a single process. Our custom server reimplements Lightdash API calls in fastmcp rather than wrapping the package.  
**Suggested fix:** None needed — the custom implementation is self-contained. If `lightdash-mcp` adds fastmcp support in the future, its API client patterns could be reused.
