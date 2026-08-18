#!/usr/bin/env bash
set -euo pipefail

echo "=== Initializing Trino Hive catalog over MinIO Parquet ==="

kubectl config use-context k3d-sandbox >/dev/null 2>&1 || true
kubectl rollout status deployment/trino --timeout="${ROLLOUT_TIMEOUT:-600s}"

trino_exec() {
  local sql="$1"
  local attempt
  for attempt in 1 2 3 4 5 6 7 8 9 10; do
    if kubectl exec deployment/trino -- trino --execute "$sql"; then
      return 0
    fi
    echo "  Trino query failed; retrying $attempt/10..."
    sleep 5
  done
  return 1
}

trino_exec "CREATE SCHEMA IF NOT EXISTS hive.raw_arena WITH (location = 's3://data-lakehouse/arena/')"
trino_exec "CREATE SCHEMA IF NOT EXISTS hive.raw_podium WITH (location = 's3://data-lakehouse/podium/')"
trino_exec "DROP SCHEMA IF EXISTS hive.analytics CASCADE"
kubectl exec deployment/dagster -- sh -c 'cd /app && env MINIO_ENDPOINT=http://minio:9000 uv run python scripts/clear_minio_prefix.py analytics/'
trino_exec "CREATE SCHEMA IF NOT EXISTS hive.analytics WITH (location = 's3://data-lakehouse/analytics/')"

trino_exec "
CREATE TABLE IF NOT EXISTS hive.raw_arena.fan_pings (
  timestamp timestamp(3),
  device_id varchar,
  beacon_id varchar,
  x_coord double,
  y_coord double,
  estimated_dwell_time integer,
  tenant_id varchar,
  generated_at timestamp(3)
)
WITH (
  external_location = 's3://data-lakehouse/arena/fan_pings/',
  format = 'PARQUET'
)"

trino_exec "
CREATE TABLE IF NOT EXISTS hive.raw_arena.pos_transactions (
  timestamp timestamp(3),
  transaction_id varchar,
  vendor_id varchar,
  item_id varchar,
  amount double,
  payment_method varchar,
  tenant_id varchar,
  generated_at timestamp(3)
)
WITH (
  external_location = 's3://data-lakehouse/arena/pos_transactions/',
  format = 'PARQUET'
)"

trino_exec "
CREATE TABLE IF NOT EXISTS hive.raw_podium.interaction_events (
  timestamp timestamp(3),
  interaction_id varchar,
  merchant_id varchar,
  customer_id varchar,
  channel varchar,
  direction varchar,
  tenant_id varchar,
  generated_at timestamp(3)
)
WITH (
  external_location = 's3://data-lakehouse/podium/interaction_events/',
  format = 'PARQUET'
)"

trino_exec "
CREATE TABLE IF NOT EXISTS hive.raw_podium.ai_telemetry (
  timestamp timestamp(3),
  interaction_id varchar,
  prompt_tokens integer,
  completion_tokens integer,
  sentiment_score double,
  latency_ms integer,
  tenant_id varchar,
  generated_at timestamp(3)
)
WITH (
  external_location = 's3://data-lakehouse/podium/ai_telemetry/',
  format = 'PARQUET'
)"

echo "=== Trino raw table smoke counts ==="
trino_exec "
SELECT 'raw_arena.fan_pings' AS table_name, count(*) AS row_count FROM hive.raw_arena.fan_pings
UNION ALL
SELECT 'raw_arena.pos_transactions', count(*) FROM hive.raw_arena.pos_transactions
UNION ALL
SELECT 'raw_podium.interaction_events', count(*) FROM hive.raw_podium.interaction_events
UNION ALL
SELECT 'raw_podium.ai_telemetry', count(*) FROM hive.raw_podium.ai_telemetry
"

echo "=== Trino initialization complete ==="
