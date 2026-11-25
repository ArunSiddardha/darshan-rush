#!/usr/bin/env bash
# Usage: secrets.sh   Creates/updates k8s secret darshan-secrets from repo/.env (KEY=VALUE lines). Never prints values.
set -euo pipefail
. "$(cd "$(dirname "$0")" && pwd)/_common.sh"
[ "${1:-}" = "-h" ] && { sed -n '2p' "$0"; exit 0; }
ENVF="$REPO/.env"
[ -f "$ENVF" ] || { echo "missing $ENVF (copy repo/.env.example)"; exit 1; }
kubectl --context "kind-$CLUSTER" apply -f "$REPO/k8s/namespace.yaml" >/dev/null
kubectl --context "kind-$CLUSTER" -n "$NS" create secret generic darshan-secrets \
  --from-env-file="$ENVF" --dry-run=client -o yaml | kubectl --context "kind-$CLUSTER" apply -f - >/dev/null
echo "darshan-secrets applied. keys: $(grep -E '^[A-Za-z_][A-Za-z0-9_]*=' "$ENVF" | cut -d= -f1 | tr '\n' ' ')"
