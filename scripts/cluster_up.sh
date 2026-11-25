#!/usr/bin/env bash
# Usage: cluster_up.sh   Creates kind cluster 'nb' (1 control-plane + 2 workers, host 8088 -> NodePort 30080) if missing.
set -euo pipefail
. "$(cd "$(dirname "$0")" && pwd)/_common.sh"
[ "${1:-}" = "-h" ] && { sed -n '2p' "$0"; exit 0; }
if kind get clusters 2>/dev/null | grep -qx "$CLUSTER"; then echo "cluster $CLUSTER exists"; else kind create cluster --config "$REPO/k8s/kind.yaml"; fi
kubectl --context "kind-$CLUSTER" get nodes
