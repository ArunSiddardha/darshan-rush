#!/usr/bin/env bash
# Usage: build_load.sh   Builds darshan:dev from repo/app and loads it into kind cluster 'nb'.
set -euo pipefail
. "$(cd "$(dirname "$0")" && pwd)/_common.sh"
[ "${1:-}" = "-h" ] && { sed -n '2p' "$0"; exit 0; }
docker build -t "$IMAGE" "$REPO/app"
kind load docker-image "$IMAGE" --name "$CLUSTER"
