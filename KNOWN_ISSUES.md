# Known Issues

Issues identified during development that are out of scope of the current phase but should be addressed in future work.

## Infrastructure

### 1. Hardcoded hostPath in Dagster manifest
**File:** `k3s/dagster.yaml:68`  
**Issue:** The Dagster deployment uses `hostPath: /workspace/de-for-fun` which only works if the repo is cloned at that exact path. Not portable to other developer machines.  
**Suggested fix:** Use a configurable volume mount or a shared PVC instead of hostPath.

### 2. MinIO uses `:latest` tag
**File:** `k3s/minio.yaml:33`  
**Issue:** The MinIO deployment uses `minio/minio:latest` which is not reproducible. Different pulls may get different versions.  
**Suggested fix:** Pin to a specific version tag (e.g., `minio/minio:RELEASE.2025-01-01T00-00-00Z`).

### 3. No health checks in k3s manifests
**Files:** `k3s/minio.yaml`, `k3s/redpanda.yaml`, `k3s/dagster.yaml`, `k3s/lightdash.yaml`  
**Issue:** None of the deployments define liveness or readiness probes. Kubernetes cannot detect if a service is unhealthy or route traffic only to ready instances.  
**Suggested fix:** Add `livenessProbe` and `readinessProbe` to each deployment's container spec.

## Orchestration

### 4. Empty Dagster definitions
**File:** `src/orchestration/definitions.py`  
**Issue:** The Dagster definitions file is empty (`Definitions()` with no assets). The Dagster UI shows nothing.  
**Scope:** This is Phase 4 work (Dagster asset definitions for generator → dbt pipeline).

### 5. No automated Redpanda topic creation in deploy script
**File:** `scripts/deploy.sh`  
**Issue:** Redpanda topics are not created during `make deploy` in the original Phase 1 script. Phase 2 adds topic creation to deploy.sh, but it relies on `rpk` being available inside the Redpanda container and uses `|| true` to ignore failures. A more robust approach would verify topic creation succeeded.  
**Suggested fix:** Add explicit topic verification with retry logic.
