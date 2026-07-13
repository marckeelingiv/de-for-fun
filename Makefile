ROWS ?= 100000

.PHONY: help setup up down deploy status dashboard generate generate-full buffer

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
