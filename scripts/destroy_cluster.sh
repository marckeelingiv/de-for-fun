#!/bin/bash
set -e

CLUSTER_NAME="sandbox"

echo "=== Destroying k3d Cluster: ${CLUSTER_NAME} ==="

if k3d cluster list | grep -q "^${CLUSTER_NAME}"; then
  k3d cluster delete "${CLUSTER_NAME}"
  echo "Cluster '${CLUSTER_NAME}' deleted successfully."
else
  echo "Cluster '${CLUSTER_NAME}' does not exist."
fi
