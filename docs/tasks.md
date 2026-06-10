# Project Tasks Checklist

This list details the sequential tasks required to build the Project Sandbox. Each task has been broken down to take under 4 hours of implementation and verification time.

## Phase 1: Environment & Infrastructure Bootstrapping (k3d, uv & Makefile)
- [x] Initialize Python environment, `pyproject.toml`, and `uv` workspace lockfile (Done by USER)
- [x] Create `k3s/postgres.yaml` manifest (Done)
- [x] Create `k3s/minio.yaml` manifest (Done)
- [x] Create `k3s/duckdb-storage.yaml` manifest (Done)
- [x] Create `k3s/dagster.yaml` manifest (Done)
- [x] Create `k3s/lightdash.yaml` manifest (Done)
- [x] Create `scripts/` orchestration scripts for k3d and manifest deployments (Done)
- [x] Create `Makefile` in project root mapping to bootstrapping scripts (Done)
- [x] Create and document system architecture in `README.md` (Done)
- [x] Write storage bootstrapping script `src/bootstrap_storage.py` to auto-create MinIO buckets (Done)

## Phase 2: Synthetic Data Generation (Polars)
- [ ] Design and implement SEG data generation schema logic in `src/generator_seg.py` (Est: 2h)
- [ ] Design and implement Podium data generation schema logic in `src/generator_podium.py` (Est: 2h)
- [ ] Combine generators into a multi-threaded Polars writing script `src/generator.py` streaming Parquet to MinIO (Est: 2h)

## Phase 3: Compute Mounting & DuckDB Setup
- [ ] Write DuckDB view registration script `src/mount_duckdb.py` to create views over MinIO Parquet files via `httpfs` (Est: 1.5h)
- [ ] Write analytical query test suite in `src/query_duckdb.py` to run aggregations on the Parquet views (Est: 1.5h)
- [ ] Write validation test `src/verify_data.py` to verify Parquet row counts and schema integrity (Est: 1.5h)

## Phase 4: dbt Models & Dagster Orchestration
- [ ] Initialize dbt project and configure `profiles.yml` for DuckDB (Est: 1.5h)
- [ ] Write SEG dbt models (staging, aggregate marts for bottlenecks and dynamic pricing) (Est: 2h)
- [ ] Write Podium dbt models (staging, aggregate marts for merchant sentiment and AI SLAs) (Est: 2h)
- [ ] Define dbt semantic layer metrics (YAML configurations for dimensions, measures, aggregates) (Est: 2h)
- [ ] Implement Dagster software-defined assets in `src/orchestration/` mapping generator -> dbt (Est: 3h)

## Phase 5: Lightdash Semantic MCP Server
- [ ] Write custom Lightdash MCP server in `src/mcp_server.py` using `fastmcp` (Est: 3h)
- [ ] Implement MCP tools for listing and querying semantic metrics from Lightdash/dbt (Est: 2h)
- [ ] Implement MCP tool for generating/saving dark-themed performance charts (Est: 2.5h)
- [ ] Run end-to-end integration test validating LLM-to-MCP query execution (Est: 2h)
