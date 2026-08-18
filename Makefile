ROWS ?= 100000
PREVIEW_NAME ?= sandbox-preview

.PHONY: help setup up down deploy status dashboard trino trino-init trino-smoke generate generate-full buffer stream stream-stop generate-continuous buffer-continuous mount query verify dbt-debug dbt-parse dbt-compile dbt-run dbt-test dbt-compile-trino dbt-run-trino lightdash-lint lightdash-deploy lightdash-upload lightdash-download lightdash-preview lightdash-stop-preview lightdash-config orchestrate mcp mcp-http test-mcp persona-review persona-conversation test-persona-review slides slides-build slides-export

help:
	@echo "Available commands:"
	@echo "  make setup         - Install local dependencies (k3d, kubectl)"
	@echo "  make up            - Spin up k3d containerized cluster"
	@echo "  make down          - Tear down k3d cluster and delete resources"
	@echo "  make deploy        - Apply postgres, minio, trino, dagster, and lightdash manifests"
	@echo "  make status        - Show status of pods and services in the cluster"
	@echo "  make dashboard     - Deploy Skooner, print access token, and start port-forwarding"
	@echo "  make trino         - Deploy Trino query service for Lightdash"
	@echo "  make trino-init    - Register MinIO Parquet tables in Trino Hive catalog"
	@echo "  make trino-smoke   - Run Trino raw table smoke counts"
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
	@echo "  make dbt-compile-trino - Compile dbt models against Trino target"
	@echo "  make dbt-run-trino - Run dbt models against Trino target"
	@echo "  make dbt-test      - Run dbt data tests"
	@echo "  make lightdash-lint    - Validate Lightdash chart/dashboard YAML locally"
	@echo "  make lightdash-deploy  - Deploy dbt semantic layer (metrics, dimensions) to Lightdash"
	@echo "  make lightdash-upload  - Upload charts and dashboards from lightdash/ to Lightdash"
	@echo "  make lightdash-download - Download charts and dashboards from Lightdash as YAML"
	@echo "  make lightdash-preview  - Create a preview project for testing changes"
	@echo "  make lightdash-stop-preview - Stop and clean up preview project"
	@echo "  make lightdash-config  - Show current Lightdash project"
	@echo "  make orchestrate   - Open access to the k3d Dagster UI"
	@echo "  make mcp          - Start MCP server (stdio, for LLM integration)"
	@echo "  make mcp-http     - Start MCP server (HTTP, port 8079)"
	@echo "  make test-mcp     - Run MCP server integration tests"
	@echo "  make persona-review - Prepare a local persona review packet (BRIEF=... ARTIFACT=... OUTPUT=...)"
	@echo "  make persona-conversation - Start an OpenCode persona session (PERSONA=... BRIEF=... ARTIFACT=...)"
	@echo "  make test-persona-review - Run persona review unit tests"
	@echo "  make slides       - Start the meetup slideshow deck"
	@echo "  make slides-build - Build the slideshow as static HTML"
	@echo "  make slides-export - Export the slideshow to PDF"

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

trino:
	@echo "=== Deploying Trino query service ==="
	@kubectl config use-context k3d-sandbox 2>/dev/null || true
	@kubectl apply -f k3s/trino.yaml
	@kubectl rollout restart deployment/trino
	@kubectl rollout status deployment/trino --timeout=600s
	@echo "Access Trino at http://localhost:8081"

trino-init: trino
	@./scripts/init_trino.sh

trino-smoke:
	@echo "=== Running Trino raw table smoke counts ==="
	@kubectl config use-context k3d-sandbox 2>/dev/null || true
	@kubectl exec deployment/trino -- trino --execute "SELECT 'raw_arena.fan_pings' AS table_name, count(*) AS row_count FROM hive.raw_arena.fan_pings UNION ALL SELECT 'raw_arena.pos_transactions', count(*) FROM hive.raw_arena.pos_transactions UNION ALL SELECT 'raw_podium.interaction_events', count(*) FROM hive.raw_podium.interaction_events UNION ALL SELECT 'raw_podium.ai_telemetry', count(*) FROM hive.raw_podium.ai_telemetry"

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

dbt-compile-trino:
	@echo "=== Compiling dbt models against Trino ==="
	@./scripts/dbt_trino.sh compile

dbt-run-trino:
	@echo "=== Running dbt models against Trino ==="
	@./scripts/dbt_trino.sh run

dbt-test:
	@echo "=== Running dbt tests ==="
	@DUCKDB_PATH=$(CURDIR)/dbt_project/target/dev.duckdb uv run dbt test --project-dir dbt_project --profiles-dir dbt_project

lightdash-lint:
	@echo "=== Linting Lightdash YAML files ==="
	@lightdash lint --path lightdash

lightdash-deploy:
	@echo "=== Deploying dbt semantic layer to Lightdash ==="
	@DUCKDB_PATH=$(CURDIR)/dbt_project/target/dev.duckdb lightdash deploy --project-dir dbt_project --profiles-dir dbt_project

lightdash-upload:
	@echo "=== Uploading charts and dashboards to Lightdash ==="
	@lightdash upload --charts-dir lightdash/charts --dashboards-dir lightdash/dashboards

lightdash-download:
	@echo "=== Downloading charts and dashboards from Lightdash ==="
	@lightdash download --charts-dir lightdash/charts --dashboards-dir lightdash/dashboards --nested

lightdash-preview:
	@echo "=== Creating Lightdash preview project ($(PREVIEW_NAME)) ==="
	@DUCKDB_PATH=$(CURDIR)/dbt_project/target/dev.duckdb lightdash preview --name $(PREVIEW_NAME) --project-dir dbt_project --profiles-dir dbt_project

lightdash-stop-preview:
	@echo "=== Stopping Lightdash preview project ($(PREVIEW_NAME)) ==="
	@lightdash stop-preview --name $(PREVIEW_NAME)

lightdash-config:
	@echo "=== Current Lightdash project ==="
	@lightdash config get-project

orchestrate:
	@echo "=== Accessing k3d Dagster UI ==="
	@kubectl config use-context k3d-sandbox 2>/dev/null || true
	@kubectl rollout status deployment/dagster --timeout=600s
	@echo "Access Dagster at http://localhost:3000"
	@kubectl port-forward svc/dagster 3000:3000

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

persona-review:
	@uv run python src/persona_review.py --brief $(BRIEF) --artifact $(ARTIFACT) --output $(OUTPUT)

persona-conversation:
	@./scripts/persona_conversation.sh "$(PERSONA)" "$(BRIEF)" "$(ARTIFACT)"

test-persona-review:
	@uv run python src/test_persona_review.py

slides:
	@echo "=== Starting Slidev meetup deck ==="
	@npm --prefix slides run dev

slides-build:
	@echo "=== Building Slidev meetup deck ==="
	@npm --prefix slides run build

slides-export:
	@echo "=== Exporting Slidev meetup deck ==="
	@npm --prefix slides run export
