#!/usr/bin/env bash
# Usage: calm.sh   Resets the demo: restarts the darshan pod (clears memory), waits ready. Does not change the Flagsmith flag.
set -euo pipefail
. "$(cd "$(dirname "$0")" && pwd)/_common.sh"
[ "${1:-}" = "-h" ] && { sed -n '2p' "$0"; exit 0; }
kubectl --context "kind-$CLUSTER" -n "$NS" rollout restart deploy/darshan
kubectl --context "kind-$CLUSTER" -n "$NS" rollout status deploy/darshan --timeout=120s
echo "Calm. Run scripts/flip.sh full open to restore flags if needed."
