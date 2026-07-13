# Known Issues

Issues identified during development that are out of scope of the current phase but should be addressed in future work.

## Infrastructure

### 1. Hardcoded hostPath in Dagster manifest
**File:** `k3s/dagster.yaml:68`  
**Issue:** The Dagster deployment uses `hostPath: /workspace/de-for-fun` which only works if the repo is cloned at that exact path. Not portable to other developer machines.  
**Suggested fix:** Use a configurable volume mount or a shared PVC instead of hostPath.

### 2. MinIO uses `:latest` tag
**File:** `k3s/minio.yaml:33`  
**Issue:** The MinIO deployment uses `minio/minio:latest` which is not reproducible. Different pulls may get different versions.  
**Suggested fix:** Pin to a specific version tag (e.g., `minio/minio:RELEASE.2025-01-01T00-00-00Z`).

### 3. No health checks in k3s manifests
**Files:** `k3s/minio.yaml`, `k3s/redpanda.yaml`, `k3s/dagster.yaml`, `k3s/lightdash.yaml`  
**Issue:** None of the deployments define liveness or readiness probes. Kubernetes cannot detect if a service is unhealthy or route traffic only to ready instances.  
**Suggested fix:** Add `livenessProbe` and `readinessProbe` to each deployment's container spec.

## Orchestration

### 4. ~~Empty Dagster definitions~~ (Resolved in Phase 4)
**File:** `src/orchestration/definitions.py`  
**Resolution:** Phase 4 implemented full Dagster asset definitions with 20 assets (generator -> buffer_writer -> verify -> 12 dbt models + time spine + 4 sources) using `dagster-dbt` for dbt model discovery.

### 5. No automated Redpanda topic creation in deploy script
**File:** `scripts/deploy.sh`  
**Issue:** Redpanda topics are not created during `make deploy` in the original Phase 1 script. Phase 2 adds topic creation to deploy.sh, but it relies on `rpk` being available inside the Redpanda container and uses `|| true` to ignore failures. A more robust approach would verify topic creation succeeded.  
**Suggested fix:** Add explicit topic verification with retry logic.

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

### 11. `data/` directory owned by root causes DuckDB persistence failure
**Files:** `src/mount_duckdb.py`, `src/query_duckdb.py`, `src/verify_data.py`  
**Issue:** The default DuckDB path `data/compute.duckdb` fails with a permission error when the `data/` directory is owned by root (which happens when k3s PVCs mount to that path). The Phase 3 scripts (`mount_duckdb.py`, `query_duckdb.py`, `verify_data.py`) work around this with the `--in-memory` flag, but this means the DuckDB state is not persisted between script invocations.  
**Suggested fix:** Fix directory permissions in the k3s manifest, or configure the DuckDB path to use a user-writable location (e.g., `/tmp/compute.duckdb`).

### 12. dbt `DUCKDB_PATH` must be absolute when running from repo root
**File:** `dbt_project/profiles.yml`  
**Issue:** The dbt profile uses `{{ env_var('DUCKDB_PATH', 'dbt_project/target/dev.duckdb') }}` which is a relative path. When running `dbt run --project-dir dbt_project` from the repo root, DuckDB tries to open the file relative to the project dir, resulting in `dbt_project/dbt_project/target/dev.duckdb` (doubled path) which doesn't exist.  
**Workaround:** Set `DUCKDB_PATH` to an absolute path: `DUCKDB_PATH=/home/marc/dev/de-for-fun/dbt_project/target/dev.duckdb uv run dbt run --project-dir dbt_project --profiles-dir dbt_project`.  
**Suggested fix:** Change the default in `profiles.yml` to use an absolute path or `~/.duckdb/dev.duckdb`, or update the Makefile dbt targets to always set `DUCKDB_PATH` to an absolute path.
