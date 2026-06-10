#!/bin/bash
set -e

CLUSTER_NAME="sandbox"

echo "=== Creating k3d Cluster: ${CLUSTER_NAME} ==="

# Check if cluster already exists
if k3d cluster list | grep -q "^${CLUSTER_NAME}"; then
  echo "Cluster '${CLUSTER_NAME}' already exists. Skipping creation."
else
  # Create cluster with mapped ports and hostPath mounting
  k3d cluster create "${CLUSTER_NAME}" \
    -p "9000:9000@loadbalancer" \
    -p "9001:9001@loadbalancer" \
    -p "3000:3000@loadbalancer" \
    -p "8080:8080@loadbalancer" \
    -v "/home/marc/dev/de-for-fun:/home/marc/dev/de-for-fun@agent:0"
  
  echo "Cluster '${CLUSTER_NAME}' created successfully."
fi
