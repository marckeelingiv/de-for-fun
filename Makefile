.PHONY: help setup up down deploy status

help:
	@echo "Available commands:"
	@echo "  make setup   - Install local dependencies (k3d, kubectl)"
	@echo "  make up      - Spin up k3d containerized cluster"
	@echo "  make down    - Tear down k3d cluster and delete resources"
	@echo "  make deploy  - Apply postgres, minio, dagster, and lightdash manifests"
	@echo "  make status  - Show status of pods and services in the cluster"

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
