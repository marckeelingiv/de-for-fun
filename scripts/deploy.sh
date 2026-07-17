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
create_topic_with_retry() {
  local topic="$1"
  local max_retries=3
  local retry=0
  while [ $retry -lt $max_retries ]; do
    if kubectl exec deployment/redpanda -- rpk topic create "$topic" -c retention.ms=3600000 2>/dev/null; then
      echo "  Created topic: $topic"
      return 0
    fi
    retry=$((retry + 1))
    if [ $retry -lt $max_retries ]; then
      echo "  Retry $retry/$max_retries for topic: $topic..."
      sleep 2
    fi
  done
  # Topic might already exist — verify it
  if kubectl exec deployment/redpanda -- rpk topic describe "$topic" >/dev/null 2>&1; then
    echo "  Topic already exists: $topic"
    return 0
  fi
  echo "  FAILED: Could not create topic: $topic"
  return 1
}

for topic in seg.fan-pings seg.pos-transactions podium.interaction-events podium.ai-telemetry; do
  create_topic_with_retry "$topic"
done

echo "=== Verifying Redpanda Topics ==="
for topic in seg.fan-pings seg.pos-transactions podium.interaction-events podium.ai-telemetry; do
  if kubectl exec deployment/redpanda -- rpk topic describe "$topic" >/dev/null 2>&1; then
    echo "  OK: $topic"
  else
    echo "  MISSING: $topic"
  fi
  done

echo "=== Setting Redpanda Topic Retention (1 hour) ==="
for topic in seg.fan-pings seg.pos-transactions podium.interaction-events podium.ai-telemetry; do
  kubectl exec deployment/redpanda -- rpk topic set-config "$topic" retention.ms=3600000 2>/dev/null || true
  echo "  Set retention.ms=3600000 on $topic"
done

echo "=== All Services Deployed and Ready! ==="
