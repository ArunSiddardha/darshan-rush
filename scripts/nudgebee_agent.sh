#!/usr/bin/env bash
# Usage: nudgebee_agent.sh <agent-key>   Installs the NudgeBee k8s agent into the current kind cluster (eBPF off: -d true).
# Get the key: app.nudgebee.com > Admin > Integrations > Kubernetes Clusters > Add K8s Account (Non-production).
set -euo pipefail
. "$(cd "$(dirname "$0")" && pwd)/_common.sh"
KEY="${1:-}"
[ -z "$KEY" ] || [ "$KEY" = "-h" ] && { sed -n '2,3p' "$0"; exit 1; }
kubectl config use-context "kind-$CLUSTER" >/dev/null
TMP="/tmp/nudgebee-agent-install"; mkdir -p "$TMP"
curl -fsSL -o "$TMP/installation.sh" https://raw.githubusercontent.com/nudgebee/k8s-agent/main/installation.sh
bash "$TMP/installation.sh" -a "$KEY" -d true
kubectl -n nudgebee-agent get pods
