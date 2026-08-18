#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROWS="${ROWS:-100000}"
SKIP_SETUP="${SKIP_SETUP:-0}"
BUFFER_WAIT_SECONDS="${BUFFER_WAIT_SECONDS:-20}"
MCP_HTTP_WAIT_SECONDS="${MCP_HTTP_WAIT_SECONDS:-5}"

BACKGROUND_PIDS=()

cleanup() {
  local pid
  for pid in "${BACKGROUND_PIDS[@]:-}"; do
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
      wait "$pid" 2>/dev/null || true
    fi
  done
}
trap cleanup EXIT
trap 'cleanup; exit 130' INT TERM

print_step() {
  printf '\n\033[1;36m==> %s\033[0m\n' "$1"
}

run_cmd() {
  print_step "$1"
  shift
  printf '+ %q' "$@"
  printf '\n'
  "$@"
}

pause_for_verification() {
  local message="$1"
  printf '\n\033[1;33mManual verification required:\033[0m %s\n' "$message"
  read -r -p "Press Enter to continue, or Ctrl+C to stop. " _
}

require_command() {
  local name="$1"
  if ! command -v "$name" >/dev/null 2>&1; then
    printf 'Missing required command: %s\n' "$name" >&2
    exit 1
  fi
}

wait_for_http() {
  local url="$1"
  local seconds="$2"
  local elapsed=0
  local status
  while (( elapsed < seconds )); do
    status="$(curl -sS -o /dev/null -w '%{http_code}' "$url" 2>/dev/null || true)"
    if [[ "$status" != "000" ]]; then
      return 0
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done
  printf 'Timed out waiting for %s after %s seconds.\n' "$url" "$seconds" >&2
  return 1
}

start_background() {
  print_step "$1"
  shift
  printf '+ %q' "$@"
  printf ' &\n'
  "$@" &
  local pid=$!
  BACKGROUND_PIDS+=("$pid")
  printf 'Started background process PID %s\n' "$pid"
}

stop_background_pid() {
  local pid="$1"
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null || true
    wait "$pid" 2>/dev/null || true
  fi
}

ensure_background_running() {
  local pid="$1"
  local label="$2"
  if ! kill -0 "$pid" 2>/dev/null; then
    wait "$pid" 2>/dev/null || true
    printf '%s exited before verification completed.\n' "$label" >&2
    exit 1
  fi
}

cd "$ROOT_DIR"

require_command make
require_command curl

print_step "Slide deck demo command test"
printf 'Repo: %s\n' "$ROOT_DIR"
printf 'Rows for generate step: %s\n' "$ROWS"

if [[ "$SKIP_SETUP" == "1" ]]; then
  printf 'Skipping make setup because SKIP_SETUP=1.\n'
else
  run_cmd "Live Demo 1: one-time setup" make setup
fi

run_cmd "Live Demo 1: create k3d cluster" make up
run_cmd "Live Demo 1: deploy services" make deploy
run_cmd "Live Demo 1: cluster status" make status
run_cmd "Live Demo 1: verify Trino warehouse over MinIO" make trino-smoke

pause_for_verification "Open and verify Dagster at http://localhost:3000 and Lightdash at http://localhost:8080. Trino is available at http://localhost:8081 for Lightdash warehouse queries. Also available: MinIO http://localhost:9001, Redpanda Console http://localhost:8083."

start_background "Live Demo 2: start buffer writer consumer" make buffer
BUFFER_PID="${BACKGROUND_PIDS[-1]}"
sleep 5
ensure_background_running "$BUFFER_PID" "make buffer"
run_cmd "Live Demo 2: generate synthetic events" make generate "ROWS=$ROWS"
printf 'Waiting %s seconds for buffer writer to flush idle batches.\n' "$BUFFER_WAIT_SECONDS"
sleep "$BUFFER_WAIT_SECONDS"
stop_background_pid "$BUFFER_PID"

run_cmd "Live Demo 3: mount DuckDB views over MinIO Parquet" make mount
run_cmd "Live Demo 3: run analytical queries" make query
run_cmd "Live Demo 3: verify data" make verify

run_cmd "dbt layer: parse project" make dbt-parse
run_cmd "dbt layer: build models" make dbt-run
run_cmd "Live Demo 4: compile semantic manifest" make dbt-compile
run_cmd "Live Demo 4: run MCP integration test" make test-mcp

start_background "AI Interface: start HTTP MCP server" make mcp-http
MCP_PID="${BACKGROUND_PIDS[-1]}"
sleep 1
ensure_background_running "$MCP_PID" "make mcp-http"
wait_for_http "http://localhost:8079" "$MCP_HTTP_WAIT_SECONDS"
pause_for_verification "HTTP MCP is running at http://localhost:8079. Verify it if needed, then continue to stop it."
stop_background_pid "$MCP_PID"

run_cmd "Live Demo 5: deploy continuous streaming pods" make stream
run_cmd "Live Demo 5: show streaming pod status" kubectl get pods -l app=generator-seg -o wide
run_cmd "Live Demo 5: show buffer writer status" kubectl get pods -l app=buffer-writer -o wide

pause_for_verification "Dagster should rebuild incrementally on schedule. If you want the UI, run make orchestrate in another terminal and verify http://localhost:3000."

run_cmd "Close: stop continuous stream" make stream-stop

printf '\nAll slide deck commands completed successfully.\n'
