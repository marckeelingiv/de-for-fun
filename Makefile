ROWS ?= 100000

.PHONY: help setup up down deploy status dashboard generate generate-full buffer stream stream-stop generate-continuous buffer-continuous mount query verify dbt-debug dbt-parse dbt-compile dbt-run dbt-test orchestrate mcp mcp-http test-mcp

help:
	@echo "Available commands:"
	@echo "  make setup         - Install local dependencies (k3d, kubectl)"
	@echo "  make up            - Spin up k3d containerized cluster"
	@echo "  make down          - Tear down k3d cluster and delete resources"
	@echo "  make deploy        - Apply postgres, minio, dagster, and lightdash manifests"
	@echo "  make status        - Show status of pods and services in the cluster"
	@echo "  make dashboard     - Deploy Skooner, print access token, and start port-forwarding"
	@echo "  make generate      - Generate synthetic data and stream to Redpanda (ROWS=$(ROWS))"
	@echo "  make generate-full - Generate 50M+ rows at full scale"
	@echo "  make buffer        - Start buffer writer (Redpanda → MinIO Parquet)"
	@echo "  make generate-continuous - Start continuous data generator (local, Ctrl+C to stop)"
	@echo "  make buffer-continuous  - Start continuous buffer writer (local, Ctrl+C to stop)"
	@echo "  make stream            - Deploy generator + buffer containers to k3d cluster"
	@echo "  make stream-stop       - Remove generator + buffer containers from k3d cluster"
	@echo "  make mount         - Mount DuckDB views over MinIO Parquet files via httpfs"
	@echo "  make query         - Run analytical queries on the Parquet views"
	@echo "  make verify        - Verify Parquet row counts and schema integrity"
	@echo "  make dbt-debug     - Check dbt connection and configuration"
	@echo "  make dbt-parse     - Parse dbt models (validate syntax)"
	@echo "  make dbt-compile   - Compile dbt models to SQL"
	@echo "  make dbt-run       - Run dbt models (build tables/views in DuckDB)"
	@echo "  make dbt-test      - Run dbt data tests"
	@echo "  make orchestrate   - Start Dagster UI for orchestration"
	@echo "  make mcp          - Start MCP server (stdio, for LLM integration)"
	@echo "  make mcp-http     - Start MCP server (HTTP, port 8079)"
	@echo "  make test-mcp     - Run MCP server integration tests"

setup:
	@./scripts/install_k3d.sh

up:
	@./scripts/create_cluster.sh

down:
	@./scripts/destroy_cluster.sh

deploy:
	@./scripts/deploy.sh

status:
	@kubectl config use-context k3d-sandbox 2>/dev/null || true
	@kubectl get pods,svc -o wide

dashboard:
	@kubectl config use-context k3d-sandbox 2>/dev/null || true
	@echo "=== Deploying Skooner Dashboard ==="
	@kubectl apply -f k3s/skooner.yaml
	@echo "=== Waiting for Skooner to be ready ==="
	@kubectl rollout status deployment/skooner -n kube-system --timeout=600s
	@echo ""
	@echo "=== Skooner Access Token ==="
	@kubectl -n kube-system create token skooner-sa
	@echo ""
	@echo "=== Starting Skooner Dashboard port-forward ==="
	@echo "Access the dashboard at http://localhost:4654"
	@kubectl -n kube-system port-forward svc/skooner 4654:80

generate:
	@echo "=== Generating synthetic data and streaming to Redpanda ==="
	@uv run python src/generator.py --rows $(ROWS)

generate-full:
	@echo "=== Generating 50M+ synthetic data (full scale) ==="
	@uv run python src/generator.py --scale full

buffer:
	@echo "=== Starting buffer writer (Redpanda → MinIO Parquet) ==="
	@uv run python src/buffer_writer.py

generate-continuous:
	@echo "=== Starting continuous generator (local, Ctrl+C to stop) ==="
	@uv run python src/generator.py --continuous

buffer-continuous:
	@echo "=== Starting continuous buffer writer (local, Ctrl+C to stop) ==="
	@uv run python src/buffer_writer.py --continuous

stream:
	@echo "=== Deploying continuous generator + buffer containers to k3d ==="
	@kubectl config use-context k3d-sandbox 2>/dev/null || true
	@kubectl apply -f k3s/generator-seg.yaml
	@kubectl apply -f k3s/generator-podium.yaml
	@kubectl apply -f k3s/buffer-writer.yaml
	@echo "=== Waiting for generator + buffer pods to be ready ==="
	@kubectl rollout status deployment/generator-seg --timeout=600s
	@kubectl rollout status deployment/generator-podium --timeout=600s
	@kubectl rollout status deployment/buffer-writer --timeout=600s
	@echo "=== Continuous stream deployed! ==="
	@echo "  Generator SEG:   producing ~200 rows/sec to seg.* topics"
	@echo "  Generator Podium: producing ~300 rows/sec to podium.* topics"
	@echo "  Buffer Writer:    flushing to MinIO every 15 minutes"
	@echo ""
	@echo "  Watch pods:   kubectl get pods -l app in (generator-seg,generator-podium,buffer-writer)"
	@echo "  Stop stream:  make stream-stop"

stream-stop:
	@echo "=== Stopping continuous generator + buffer containers ==="
	@kubectl config use-context k3d-sandbox 2>/dev/null || true
	@kubectl delete deployment generator-seg generator-podium buffer-writer 2>/dev/null || true
	@echo "=== Stream stopped ==="

mount:
	@echo "=== Mounting DuckDB views over MinIO Parquet files ==="
	@DUCKDB_PATH=$(CURDIR)/dbt_project/target/dev.duckdb uv run python src/mount_duckdb.py

query:
	@echo "=== Running analytical queries on Parquet views ==="
	@DUCKDB_PATH=$(CURDIR)/dbt_project/target/dev.duckdb uv run python src/query_duckdb.py

verify:
	@echo "=== Verifying Parquet data integrity ==="
	@DUCKDB_PATH=$(CURDIR)/dbt_project/target/dev.duckdb uv run python src/verify_data.py

dbt-debug:
	@echo "=== Checking dbt connection ==="
	@DUCKDB_PATH=$(CURDIR)/dbt_project/target/dev.duckdb uv run dbt debug --project-dir dbt_project --profiles-dir dbt_project

dbt-parse:
	@echo "=== Parsing dbt models ==="
	@uv run dbt parse --project-dir dbt_project --profiles-dir dbt_project

dbt-compile:
	@echo "=== Compiling dbt models ==="
	@DUCKDB_PATH=$(CURDIR)/dbt_project/target/dev.duckdb uv run dbt compile --project-dir dbt_project --profiles-dir dbt_project

dbt-run:
	@echo "=== Running dbt models ==="
	@DUCKDB_PATH=$(CURDIR)/dbt_project/target/dev.duckdb uv run dbt run --project-dir dbt_project --profiles-dir dbt_project

dbt-test:
	@echo "=== Running dbt tests ==="
	@DUCKDB_PATH=$(CURDIR)/dbt_project/target/dev.duckdb uv run dbt test --project-dir dbt_project --profiles-dir dbt_project

orchestrate:
	@echo "=== Starting Dagster UI ==="
	@uv run dagster dev -h 0.0.0.0 -p 3000 -f src/orchestration/definitions.py

mcp:
	@echo "=== Starting MCP server (stdio transport for LLM integration) ==="
	@uv run python src/mcp_server.py

mcp-http:
	@echo "=== Starting MCP server (HTTP transport) ==="
	@echo "Access at http://localhost:8079"
	@uv run python src/mcp_server.py --transport http --port 8079

test-mcp:
	@echo "=== Running MCP server integration tests ==="
	@uv run python src/test_mcp_server.py
