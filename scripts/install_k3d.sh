#!/bin/bash
set -e

echo "=== Checking & Installing Dependencies ==="

# Check and install k3d
if ! command -v k3d &> /dev/null; then
  echo "k3d not found. Installing k3d..."
  curl -s https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | TAG=v5.6.3 bash
else
  echo "k3d is already installed: $(k3d --version | head -n 1)"
fi

# Check and install kubectl
if ! command -v kubectl &> /dev/null; then
  echo "kubectl not found. Installing kubectl..."
  curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
  chmod +x kubectl
  mkdir -p "$HOME/.local/bin"
  mv kubectl "$HOME/.local/bin/kubectl"
  echo "kubectl installed successfully to $HOME/.local/bin/kubectl"
else
  echo "kubectl is already installed: $(kubectl version --client --output=yaml | grep gitVersion | head -n 1)"
fi

echo "=== Dependencies Check Complete ==="
