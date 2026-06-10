# Project Tasks Checklist

This list details the sequential tasks required to build the Project Sandbox. Each task has been broken down to take under 4 hours of implementation and verification time.

## Phase 1: Environment & Infrastructure Bootstrapping (k3s & uv)
- [ ] Initialize Python environment, `pyproject.toml`, and `uv` workspace lockfile (Est: 0.5h)
- [ ] Create `k8s/postgres.yaml` manifest and verify container startup/health (Est: 1h)
- [ ] Create `k8s/minio.yaml` manifest (PVC, Deployment, Service) and verify console access (Est: 1h)
- [ ] Create `k8s/clickhouse.yaml` manifest (StatefulSet, Service, ConfigMap) and verify client connection (Est: 1.5h)
- [ ] Create `k8s/dagster.yaml` manifest and verify daemon/webserver execution (Est: 1.5h)
- [ ] Create `k8s/lightdash.yaml` manifest and verify connection to ClickHouse/Postgres metadata (Est: 1.5h)
- [ ] Write storage bootstrapping script `src/bootstrap_storage.py` to auto-create MinIO buckets (Est: 1h)

## Phase 2: Synthetic Data Generation (Polars)
- [ ] Design and implement SEG data generation schema logic in `src/generator_seg.py` (Est: 2h)
- [ ] Design and implement Podium data generation schema logic in `src/generator_podium.py` (Est: 2h)
- [ ] Combine generators into a multi-threaded Polars writing script `src/generator.py` streaming Parquet to MinIO (Est: 2h)

## Phase 3: Compute Mounting & ClickHouse vs. DuckDB
- [ ] Write `src/mount_clickhouse.sql` using the native `s3()` function to register views over MinIO Parquet (Est: 1.5h)
- [ ] Write `src/compute_duckdb.py` to query the same MinIO files via DuckDB's `httpfs` extension (Est: 1.5h)
- [ ] Write verification test `src/verify_compute.py` running identical SQL on ClickHouse & DuckDB (Est: 1.5h)

## Phase 4: dbt Models & Dagster Orchestration
- [ ] Initialize dbt project and configure `profiles.yml` for ClickHouse and DuckDB (Est: 1.5h)
- [ ] Write SEG dbt models (staging, aggregate marts for bottlenecks and dynamic pricing) (Est: 2h)
- [ ] Write Podium dbt models (staging, aggregate marts for merchant sentiment and AI SLAs) (Est: 2h)
- [ ] Define dbt semantic layer metrics (YAML configurations for dimensions, measures, aggregates) (Est: 2h)
- [ ] Implement Dagster software-defined assets in `src/orchestration/` mapping generator -> dbt (Est: 3h)

## Phase 5: Lightdash Semantic MCP Server
- [ ] Write custom Lightdash MCP server in `src/mcp_server.py` using `fastmcp` (Est: 3h)
- [ ] Implement MCP tools for listing and querying semantic metrics from Lightdash/dbt (Est: 2h)
- [ ] Implement MCP tool for generating/saving dark-themed performance charts (Est: 2.5h)
- [ ] Run end-to-end integration test validating LLM-to-MCP query execution (Est: 2h)
