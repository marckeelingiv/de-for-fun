#!/bin/bash
set -e

echo "=== Deploying Manifests to k3d Cluster ==="

# Set k3d kubectl context
kubectl config use-context k3d-sandbox || true

wait_for_deployment() {
  kubectl rollout status "deployment/$1" --timeout="${ROLLOUT_TIMEOUT:-600s}"
}

# Apply storage PVCs first
kubectl apply -f k3s/duckdb-storage.yaml

# Apply backing services first. On a fresh k3d cluster these image pulls can take
# several minutes, so keep the rollout timeout longer than kubectl's default.
kubectl apply -f k3s/postgres.yaml
kubectl apply -f k3s/minio.yaml
kubectl apply -f k3s/redpanda.yaml

echo "=== Waiting for backing services to be ready ==="
wait_for_deployment postgres
wait_for_deployment minio
wait_for_deployment redpanda

# Apply services that depend on Postgres, MinIO, and Redpanda.
kubectl apply -f k3s/dagster.yaml
kubectl apply -f k3s/lightdash.yaml

echo "=== Waiting for application services to be ready ==="
wait_for_deployment redpanda-console
wait_for_deployment dagster
wait_for_deployment lightdash

echo "=== Bootstrapping MinIO Storage ==="
kubectl exec deployment/dagster -- sh -c 'cd /app && env MINIO_ENDPOINT=http://minio:9000 uv run python src/bootstrap_storage.py'

echo "=== Creating Redpanda Topics ==="
for topic in seg.fan-pings seg.pos-transactions podium.interaction-events podium.ai-telemetry; do
  kubectl exec deployment/redpanda -- rpk topic create "$topic" || true
done

echo "=== All Services Deployed and Ready! ==="
