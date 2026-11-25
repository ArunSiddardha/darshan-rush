#!/usr/bin/env bash
# Usage: status.sh   Shows pods, restart counts, last termination reason and recent OOM/Kill events in namespace darshan.
set -uo pipefail
. "$(cd "$(dirname "$0")" && pwd)/_common.sh"
[ "${1:-}" = "-h" ] && { sed -n '2p' "$0"; exit 0; }
K="kubectl --context kind-$CLUSTER -n $NS"
$K get pods -o wide
echo "--- last state"
$K get pods -l app=darshan -o jsonpath='{range .items[*]}{.metadata.name}{" restarts="}{.status.containerStatuses[0].restartCount}{" last="}{.status.containerStatuses[0].lastState.terminated.reason}{"\n"}{end}'
echo "--- events (OOM/Kill/BackOff)"
$K get events --sort-by=.lastTimestamp 2>/dev/null | grep -Ei 'oom|kill|backoff|unhealthy' | tail -10 || echo "none"
