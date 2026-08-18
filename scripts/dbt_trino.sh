#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <dbt-command> [args...]" >&2
  exit 2
fi

kubectl config use-context k3d-sandbox >/dev/null 2>&1 || true
kubectl rollout status deployment/trino --timeout="${ROLLOUT_TIMEOUT:-600s}"

kubectl port-forward svc/trino 8081:8081 >/tmp/project-sandbox-trino-port-forward.log 2>&1 &
PORT_FORWARD_PID="$!"

cleanup() {
  kill "$PORT_FORWARD_PID" >/dev/null 2>&1 || true
  wait "$PORT_FORWARD_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

for _ in 1 2 3 4 5 6 7 8 9 10; do
  if curl -sS -o /dev/null http://localhost:8081/v1/info; then
    break
  fi
  sleep 1
done

if ! curl -sS -o /dev/null http://localhost:8081/v1/info; then
  echo "Timed out waiting for local Trino port-forward. See /tmp/project-sandbox-trino-port-forward.log" >&2
  exit 1
fi

uv run dbt "$@" --project-dir dbt_project --profiles-dir dbt_project --target trino
