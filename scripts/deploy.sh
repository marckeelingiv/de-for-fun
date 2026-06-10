#!/bin/bash
set -e

echo "=== Deploying Manifests to k3d Cluster ==="

# Set k3d kubectl context
kubectl config use-context k3d-sandbox || true

# Apply storage PVCs first
kubectl apply -f k3s/duckdb-storage.yaml

# Apply remaining manifests
kubectl apply -f k3s/postgres.yaml
kubectl apply -f k3s/minio.yaml
kubectl apply -f k3s/dagster.yaml
kubectl apply -f k3s/lightdash.yaml

echo "=== Waiting for deployments to be ready ==="
kubectl rollout status deployment/postgres --timeout=120s
kubectl rollout status deployment/minio --timeout=120s
kubectl rollout status deployment/dagster --timeout=120s
kubectl rollout status deployment/lightdash --timeout=120s

echo "=== All Services Deployed and Ready! ==="
