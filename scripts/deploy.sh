#!/usr/bin/env bash
# Usage: deploy.sh   Applies namespace, deployment, service and waits for rollout. Run secrets.sh first.
set -euo pipefail
. "$(cd "$(dirname "$0")" && pwd)/_common.sh"
[ "${1:-}" = "-h" ] && { sed -n '2p' "$0"; exit 0; }
K="kubectl --context kind-$CLUSTER"
$K apply -f "$REPO/k8s/namespace.yaml" -f "$REPO/k8s/deployment.yaml" -f "$REPO/k8s/service.yaml"
# public URL (quick tunnel) is passed as env so the judge page QR points at it
if [ -s "$REPO/metrics/public_url.txt" ]; then
  $K -n "$NS" set env deploy/darshan "PUBLIC_URL=$(tr -d '[:space:]' < "$REPO/metrics/public_url.txt")" >/dev/null
fi
$K -n "$NS" rollout restart deploy/darshan >/dev/null
$K -n "$NS" rollout status deploy/darshan --timeout=180s
echo "Darshan: http://localhost:8088  Volunteer: http://localhost:8088/volunteer"
